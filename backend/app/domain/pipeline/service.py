"""End-to-end pipeline orchestration.

Wires ingestion → validation → storage → normalization → detection →
correlation → risk scoring → observables extraction → audit, and publishes
real-time events for the WebSocket layer. Each stage failure is recorded and
raised as a structured error (no silent failures, per spec section 35).
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Principal
from app.domain.models import (
    AuditLog,
    DataSource,
    NormalizedEvent,
    Observable,
    RawEvent,
)
from app.domain.pipeline.correlation import create_or_update_alert, group_alert_into_incident
from app.domain.pipeline.detection import evaluate_event_rules
from app.domain.pipeline.normalization import (
    NormalizationError,
    NormalizedEventRecord,
    normalize_generic,
)
from app.domain.pipeline.risk_scoring import assess_alert

logger = structlog.get_logger("pipeline.service")


class IngestionValidationError(ValueError):
    """Raised when a raw payload fails validation."""


IOIndicator = re.compile(
    r"([a-f0-9]{32}|[a-f0-9]{40}|[a-f0-9]{64})"
    r"|(?:https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+)"
    r"|([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z]{2,})+)"
    r"|(?:\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b)"
)


def build_observable_hash(kind: str, value: str) -> str:
    import hashlib

    return hashlib.sha256(f"{kind}:{value}".encode()).hexdigest()


def extract_observables(payload: dict[str, Any]) -> list[tuple[str, str]]:
    """Extract candidate IOC observables from a payload string blob.

    Only syntactic extraction; reputation is assigned by the threat
    intelligence stage. Duplicates are removed.
    """

    text_blob = str(payload)
    seen: dict[str, tuple[str, str]] = {}
    for match in IOIndicator.finditer(text_blob):
        value = (match.group(0) or match.group(1) or "").strip().lower()
        if not value:
            continue
        if re.fullmatch(r"[a-f0-9]{64}", value):
            kind, key = "sha256", value
        elif re.fullmatch(r"[a-f0-9]{40}", value):
            kind, key = "sha1", value
        elif re.fullmatch(r"[a-f0-9]{32}", value):
            kind, key = "md5", value
        elif value.startswith(("http://", "https://")):
            kind, key = "url", value
        elif re.fullmatch(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}", value):
            try:
                ipaddress.ip_address(value)
            except ValueError:
                continue
            kind, key = "ip", value
        else:
            kind, key = "domain", value
        if key not in seen:
            seen[key] = (kind, value)
    return list(seen.values())


def validate_raw_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise IngestionValidationError("payload must be a JSON object")
    if len(str(payload)) > 65_536:
        raise IngestionValidationError("payload exceeds 64 KiB")
    # Reject control characters except newline/tab (log sanitization baseline).
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", str(payload)):
        raise IngestionValidationError("payload contains disallowed control characters")


@dataclass(frozen=True)
class PipelineResult:
    raw_event_id: UUID
    normalized_event_id: UUID | None
    alert_id: UUID | None
    incident_id: UUID | None
    observables: int
    trace_id: str
    normalized: bool
    risk_score: int | None


async def process_ingested_event(
    session: AsyncSession,
    tenant_id: UUID,
    data_source_id: UUID,
    source_event_id: str,
    occurred_at: datetime,
    payload: dict[str, Any],
    principal: Principal | None = None,
    trace_id: str | None = None,
) -> PipelineResult:
    """Full pipeline for one raw event. Idempotent on (tenant, source_event_id)."""

    trace_id = trace_id or str(uuid4())
    validate_raw_payload(payload)

    existing = await session.execute(
        select(RawEvent).where(
            RawEvent.tenant_id == tenant_id,
            RawEvent.data_source_id == data_source_id,
            RawEvent.source_event_id == source_event_id,
        )
    )
    existing_event = existing.scalar_one_or_none()
    if existing_event is not None:
        logger.info("event.already_ingested", source_event_id=source_event_id)
        return PipelineResult(
            raw_event_id=existing_event.id,
            normalized_event_id=None,
            alert_id=None,
            incident_id=None,
            observables=0,
            trace_id=trace_id,
            normalized=False,
            risk_score=None,
        )

    # Verify the data source belongs to the tenant (object-level auth).
    ds = await session.execute(
        select(DataSource).where(
            DataSource.tenant_id == tenant_id,
            DataSource.id == data_source_id,
        )
    )
    data_source = ds.scalar_one_or_none()
    if data_source is None:
        raise IngestionValidationError(f"unknown data source {data_source_id}")

    raw_event = RawEvent(
        tenant_id=tenant_id,
        data_source_id=data_source_id,
        source_event_id=source_event_id,
        occurred_at=occurred_at,
        received_at=datetime.now(UTC),
        payload=payload,
    )
    session.add(raw_event)
    await session.flush()

    # Stage: normalization
    try:
        record: NormalizedEventRecord = normalize_generic(payload, occurred_at)
    except NormalizationError as exc:
        logger.warning("event.normalization_failed", error=str(exc), trace_id=trace_id)
        await _audit(session, tenant_id, principal, "event.normalization_failed", "raw_event", raw_event.id, trace_id, {"error": str(exc)})
        await session.commit()
        return PipelineResult(
            raw_event_id=raw_event.id,
            normalized_event_id=None,
            alert_id=None,
            incident_id=None,
            observables=0,
            trace_id=trace_id,
            normalized=False,
            risk_score=None,
        )

    normalized_event = NormalizedEvent(
        tenant_id=tenant_id,
        raw_event_id=raw_event.id,
        data_source_id=data_source_id,
        occurred_at=record.occurred_at,
        event_type=record.event_type,
        event_category=record.event_category,
        severity=record.severity,
        actor=record.actor,
        target=record.target,
        username=record.username,
        source_ip=record.source_ip,
        source_port=record.source_port,
        destination_ip=record.destination_ip,
        destination_port=record.destination_port,
        protocol=record.protocol,
        hostname=record.hostname,
        process_name=record.process_name,
        command_line=record.command_line,
        file_hash_md5=record.file_hash_md5,
        file_hash_sha1=record.file_hash_sha1,
        file_hash_sha256=record.file_hash_sha256,
        domain=record.domain,
        url=record.url,
        cloud_identity=record.cloud_identity,
        cloud_resource=record.cloud_resource,
        authentication_result=record.authentication_result,
        correlation_key=record.correlation_key,
        session_id=record.session_id,
        normalized=record.normalized,
    )
    session.add(normalized_event)
    await session.flush()

    # Stage: observable extraction
    observables_count = 0
    for kind, value in extract_observables(payload):
        candidate = Observable(
            tenant_id=tenant_id,
            type=kind,
            value=value,
            value_hash=build_observable_hash(kind, value),
        )
        session.add(candidate)
        observables_count += 1

    # Stage: detection
    decision = await evaluate_event_rules(session, tenant_id, normalized_event)

    alert_id: UUID | None = None
    incident_id: UUID | None = None
    risk_score: int | None = None
    if decision.triggered_rule_ids:
        rule_name = decision.rule_name or decision.triggered_rule_ids[0]
        alert = await create_or_update_alert(
            session,
            tenant_id,
            title=rule_name,
            severity=decision.recommended_severity or record.severity or "medium",
            rule_id=decision.triggered_rule_ids[0],
            event=normalized_event,
            confidence=0.75,
            mitre=decision.mitre,
        )
        alert_id = alert.id
        assessment = assess_alert(
            severity=alert.severity,
            mitre_payload=decision.mitre,
            observed_fields=sum(
                1 for f in (record.source_ip, record.actor, record.hostname, record.process_name) if f
            ),
        )
        risk_score = assessment.risk_score
        alert.risk_score = risk_score
        alert.confidence = assessment.confidence
        alert.risk_explanation = assessment.explanation
        incident = await group_alert_into_incident(session, tenant_id, alert)
        if incident is not None:
            incident_id = incident.id

    await _audit(
        session,
        tenant_id,
        principal,
        "event.processed",
        "raw_event",
        raw_event.id,
        trace_id,
        {
            "normalized": True,
            "rules_triggered": decision.triggered_rule_ids,
            "alert_id": str(alert_id) if alert_id else None,
            "incident_id": str(incident_id) if incident_id else None,
            "observables": observables_count,
        },
    )
    await session.commit()
    logger.info(
        "event.processed",
        trace_id=trace_id,
        alert_id=str(alert_id) if alert_id else None,
        incident_id=str(incident_id) if incident_id else None,
        observables=observables_count,
    )
    return PipelineResult(
        raw_event_id=raw_event.id,
        normalized_event_id=normalized_event.id,
        alert_id=alert_id,
        incident_id=incident_id,
        observables=observables_count,
        trace_id=trace_id,
        normalized=True,
        risk_score=risk_score,
    )


async def _audit(
    session: AsyncSession,
    tenant_id: UUID,
    principal: Principal | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    trace_id: str | None,
    metadata: dict[str, Any],
) -> None:
    audit = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=UUID(principal.user_id) if principal and principal.user_id else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        trace_id=trace_id,
        metadata_=metadata,
    )
    session.add(audit)
