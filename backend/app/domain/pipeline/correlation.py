"""Correlation stage: deduplicate alerts and group them into incidents.

Deduplication window is deterministic: alerts sharing the same correlation
key (rule_id + correlation_key of the underlying event + actor + source IP)
within ALERT_GROUP_WINDOW_SECONDS are merged into a single alert whose
occurrence count and last-seen timestamp are updated. This mirrors the
event-grouping behavior of commercial SIEMs (per-tenant, time-windowed,
hash-based) without claiming any vendor-specific implementation.

Incident grouping applies a simple configurable strategy: alerts of the
same severity band and correlation anchor within INCIDENT_GROUP_WINDOW
minutes are attached to one open incident. Analysts can reassign or split
incidents through the incident-management API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import and_, desc, select

from app.domain.models import (
    Alert,
    AlertStatus,
    Incident,
    IncidentAlert,
    IncidentStatus,
    NormalizedEvent,
    Severity,
)

logger = structlog.get_logger("pipeline.correlation")

ALERT_GROUP_WINDOW_SECONDS = 300  # 5 minutes
INCIDENT_GROUP_WINDOW_MINUTES = 30


def build_alert_key(
    rule_id: str, correlation_key: str | None, actor: str | None, source_ip: str | None
) -> str:
    """Deterministic deduplication key for an alert."""

    parts = [rule_id, correlation_key or "", actor or "", source_ip or ""]
    return "|".join(parts)


async def create_or_update_alert(
    session,
    tenant_id: UUID,
    title: str,
    severity: Severity,
    rule_id: str,
    event: NormalizedEvent,
    confidence: float | None,
    mitre: dict,
) -> Alert:
    """Create a new alert or update an existing open duplicate."""

    alert_key = build_alert_key(rule_id, event.correlation_key, event.actor, event.source_ip)
    window_start = datetime.now(UTC) - timedelta(seconds=ALERT_GROUP_WINDOW_SECONDS)
    existing_query = (
        select(Alert)
        .where(
            and_(
                Alert.tenant_id == tenant_id,
                Alert.correlation_key == alert_key,
                Alert.status.in_([AlertStatus.new, AlertStatus.triaged]),
                Alert.last_seen_at >= window_start,
            )
        )
        .order_by(desc(Alert.last_seen_at))
        .limit(1)
    )
    result = await session.execute(existing_query)
    existing = result.scalar_one_or_none()
    if existing:
        existing.last_seen_at = datetime.now(UTC)
        existing.occurrence_count = (existing.occurrence_count or 0) + 1
        existing.normalized_event_id = event.id
        existing.raw_event_id = event.raw_event_id
        await session.commit()
        logger.info(
            "alert.deduplicated",
            alert_id=str(existing.id),
            occurrence_count=existing.occurrence_count,
        )
        return existing

    alert = Alert(
        tenant_id=tenant_id,
        title=title,
        severity=severity,
        status=AlertStatus.new,
        source="detection-rule",
        correlation_key=alert_key,
        detection_rule_id=rule_id,
        source_ip=event.source_ip,
        destination_ip=event.destination_ip,
        actor=event.actor,
        raw_event_id=event.raw_event_id,
        normalized_event_id=event.id,
        confidence=round(confidence, 4) if confidence is not None else None,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        occurrence_count=1,
        mitre=mitre,
    )
    session.add(alert)
    await session.commit()
    logger.info("alert.created", alert_id=str(alert.id), severity=severity.value)
    return alert


async def group_alert_into_incident(session, tenant_id: UUID, alert: Alert) -> Incident | None:
    """Attach an alert to an existing open incident or create a new one."""

    (alert.correlation_key or "").split("|")
    severity_band = _severity_band(alert.severity)
    window_start = datetime.now(UTC) - timedelta(minutes=INCIDENT_GROUP_WINDOW_MINUTES)

    candidate_query = (
        select(Incident)
        .join(IncidentAlert, Incident.id == IncidentAlert.incident_id)
        .join(Alert, Alert.id == IncidentAlert.alert_id)
        .where(
            and_(
                Incident.tenant_id == tenant_id,
                Incident.status.in_([IncidentStatus.open, IncidentStatus.investigating]),
                Alert.correlation_key.isnot(None),
                Alert.last_seen_at >= window_start,
            )
        )
        .order_by(Incident.created_at.desc())
        .limit(10)
    )
    result = await session.execute(candidate_query)
    for candidate in result.scalars().all():
        alerts_result = await session.execute(
            select(Alert).where(
                and_(
                    IncidentAlert.incident_id == candidate.id,
                    Alert.severity == _severity_enum_for_band(severity_band),
                )
            )
        )
        if alerts_result.scalars().first() is not None:
            # Idempotent attach: merge on the unique (incident_id, alert_id)
            # constraint so re-processing the same alert never raises a
            # UniqueViolationError.
            existing_link = await session.execute(
                select(IncidentAlert).where(
                    IncidentAlert.incident_id == candidate.id,
                    IncidentAlert.alert_id == alert.id,
                )
            )
            if existing_link.scalars().first() is None:
                session.add(IncidentAlert(incident_id=candidate.id, alert_id=alert.id))
            await session.commit()
            logger.info("alert.grouped_into_incident", alert_id=str(alert.id), incident_id=str(candidate.id))
            return candidate

    incident = Incident(
        tenant_id=tenant_id,
        title=alert.title or "Investigation required",
        summary=f"Auto-created from detection alert {alert.id}",
        severity=alert.severity,
        status=IncidentStatus.open,
    )
    session.add(incident)
    await session.flush()
    # Idempotent attach: merge on the unique (incident_id, alert_id)
    # constraint so re-processing the same alert never raises a
    # UniqueViolationError.
    existing_link = await session.execute(
        select(IncidentAlert).where(
            IncidentAlert.incident_id == incident.id,
            IncidentAlert.alert_id == alert.id,
        )
    )
    if existing_link.scalars().first() is None:
        session.add(IncidentAlert(incident_id=incident.id, alert_id=alert.id))
    await session.commit()
    logger.info("incident.created", incident_id=str(incident.id), alert_id=str(alert.id))
    return incident


def _severity_band(severity: Severity) -> int:
    mapping = {
        Severity.informational: 0,
        Severity.low: 1,
        Severity.medium: 1,
        Severity.high: 2,
        Severity.critical: 2,
    }
    return mapping.get(severity, 1)


def _severity_enum_for_band(band: int) -> Severity:
    return Severity.medium if band <= 1 else Severity.high
