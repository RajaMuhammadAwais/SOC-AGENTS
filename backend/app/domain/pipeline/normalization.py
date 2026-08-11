"""Canonical security event normalization.

Transforms connector-specific raw event payloads into the platform's
canonical internal event model (see docs/architecture/canonical-event-model.md).
Normalization is deterministic: no LLM calls, no network access, no randomness.
Every connector provides its own field-mapping table; unmapped fields are
preserved in the `normalized` JSONB context column for later review.

Field semantics are aligned with industry concepts (OCSF activity classes,
ECS naming) but the platform does not claim formal OCSF/ECS compliance.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import ciso8601
import structlog

logger = structlog.get_logger("pipeline.normalization")

MAX_PAYLOAD_SIZE = 65_536  # raw payload cap in characters


class NormalizationError(ValueError):
    """Raised when a raw payload cannot be normalized."""


FIELD_MAX_LENGTHS = {
    "event_type": 120,
    "event_category": 80,
    "actor": 255,
    "target": 255,
    "username": 255,
    "source_ip": 64,
    "destination_ip": 64,
    "protocol": 32,
    "hostname": 255,
    "process_name": 255,
    "file_hash_md5": 32,
    "file_hash_sha1": 40,
    "file_hash_sha256": 64,
    "domain": 255,
    "cloud_identity": 255,
    "cloud_resource": 255,
    "authentication_result": 64,
    "correlation_key": 255,
    "session_id": 255,
}

ALLOWED_AUTHENTICATION_RESULTS = {
    "success",
    "failure",
    "partial",
    "unknown",
    "locked",
}

VALID_PROTOCOLS = {"tcp", "udp", "icmp", "dns", "http", "https", "tls", "ssh", "ftp", "smtp", "smb", "rdp", "unknown"}

HASH_PATTERN = re.compile(r"^[0-9a-f]{32}$|^[0-9a-f]{40}$|^[0-9a-f]{64}$", re.IGNORECASE)
IP_PATTERN = re.compile(r"^[0-9a-fA-F:.]{7,64}$")
HOSTNAME_PATTERN = re.compile(r"^([a-zA-Z0-9._-]{1,253})$")


def is_ip_address(value: str | None) -> bool:
    if not value:
        return False
    if not IP_PATTERN.match(value):
        return False
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def validate_hash(value: str | None, *, kind: str) -> bool:
    if not value:
        return False
    if kind == "md5" and len(value) != 32:
        return False
    if kind == "sha1" and len(value) != 40:
        return False
    if kind == "sha256" and len(value) != 64:
        return False
    return bool(HASH_PATTERN.match(value))


@dataclass(frozen=True)
class NormalizedEventRecord:
    """Fully validated canonical event ready for persistence."""

    occurred_at: datetime
    event_type: str
    event_category: str | None = None
    event_class: int | None = None
    activity_id: int | None = None
    severity: str | None = None
    actor: str | None = None
    target: str | None = None
    username: str | None = None
    source_ip: str | None = None
    source_port: int | None = None
    destination_ip: str | None = None
    destination_port: int | None = None
    protocol: str | None = None
    hostname: str | None = None
    process_name: str | None = None
    command_line: str | None = None
    file_hash_md5: str | None = None
    file_hash_sha1: str | None = None
    file_hash_sha256: str | None = None
    domain: str | None = None
    url: str | None = None
    cloud_identity: str | None = None
    cloud_resource: str | None = None
    authentication_result: str | None = None
    correlation_key: str | None = None
    session_id: str | None = None
    normalized: dict[str, Any] = field(default_factory=dict)


def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value.strip()[:max_length] or None


def _port(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return None if not 0 <= value <= 65535 else value
    if isinstance(value, str) and value.strip().isdigit():
        numeric = int(value.strip())
        return None if not 0 <= numeric <= 65535 else numeric
    return None


def _ip(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if is_ip_address(value) else None


def _severity(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower() or None


def _auth_result(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().lower() if value.strip().lower() in ALLOWED_AUTHENTICATION_RESULTS else None


def _hash(value: Any, kind: str) -> str | None:
    if not isinstance(value, str):
        return None
    return value.lower().strip() if validate_hash(value, kind=kind) else None


class ConnectorNormalizer:
    """Base connector normalizer using an explicit field-mapping table.

    Each connector subclass declares a mapping from payload field names to
    canonical field names (with optional value transformations), plus optional
    default values and a correlation-key builder.
    """

    connector_name: str = "generic"
    field_mapping: dict[str, str] = {}
    defaults: dict[str, Any] = {}

    def normalize(self, payload: dict[str, Any], occurred_at: datetime) -> NormalizedEventRecord:
        if len(str(payload)) > MAX_PAYLOAD_SIZE:
            raise NormalizationError("payload exceeds maximum allowed size")
        if not isinstance(payload, dict):
            raise NormalizationError("payload must be a JSON object")

        record = dict(self.defaults)
        for source_field, canonical_field in self.field_mapping.items():
            value = payload.get(source_field)
            if value is None:
                continue
            transform = getattr(self, f"_t_{canonical_field}", None)
            record[canonical_field] = transform(value) if transform else value
        # Connector can override derived fields
        self.derive(record, payload)
        if not isinstance(record.get("occurred_at"), datetime):
            record["occurred_at"] = occurred_at
        record.setdefault("event_type", self.connector_name)

        return self._build_record(record, payload)

    def derive(self, record: dict[str, Any], payload: dict[str, Any]) -> None:
        """Hook for connector-specific derivation (e.g., building a
        correlation key from username + hostname)."""

    def _t_occurred_at(self, value: Any) -> datetime | None:
        """Coerce common timestamp representations to a timezone-aware
        datetime. Returns None on unparseable values so the caller falls
        back to the ingestion-supplied occurred_at."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=UTC)
            except (ValueError, OSError):
                return None
        if isinstance(value, str):
            for pattern in (
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S%z",
                "%b %d %H:%M:%S",
            ):
                try:
                    parsed = ciso8601.parse_datetime(value)
                    if parsed is not None:
                        return parsed
                except ValueError:
                    pass
                try:
                    parsed = datetime.strptime(value, pattern)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=UTC)
                    return parsed
                except ValueError:
                    continue
        return None

    def _build_record(self, record: dict[str, Any], payload: dict[str, Any]) -> NormalizedEventRecord:
        return NormalizedEventRecord(
            occurred_at=record["occurred_at"],
            event_type=_truncate(str(record["event_type"]), FIELD_MAX_LENGTHS["event_type"]) or "unknown",
            event_category=_truncate(str(record.get("event_category")), FIELD_MAX_LENGTHS["event_category"]),
            event_class=record.get("event_class"),
            activity_id=record.get("activity_id"),
            severity=_severity(record.get("severity")),
            actor=_truncate(str(record.get("actor")), FIELD_MAX_LENGTHS["actor"]) if record.get("actor") is not None else None,
            target=_truncate(str(record.get("target")), FIELD_MAX_LENGTHS["target"]) if record.get("target") is not None else None,
            username=_truncate(str(record.get("username")), FIELD_MAX_LENGTHS["username"]) if record.get("username") is not None else None,
            source_ip=_ip(record.get("source_ip")),
            source_port=_port(record.get("source_port")),
            destination_ip=_ip(record.get("destination_ip")),
            destination_port=_port(record.get("destination_port")),
            protocol=_truncate(str(record.get("protocol")), FIELD_MAX_LENGTHS["protocol"]).lower()
            if record.get("protocol") else None,
            hostname=_truncate(str(record.get("hostname")), FIELD_MAX_LENGTHS["hostname"]) if record.get("hostname") is not None else None,
            process_name=_truncate(str(record.get("process_name")), FIELD_MAX_LENGTHS["process_name"]) if record.get("process_name") is not None else None,
            command_line=_truncate(str(record.get("command_line")), 4096) if record.get("command_line") is not None else None,
            file_hash_md5=_hash(record.get("file_hash_md5"), "md5"),
            file_hash_sha1=_hash(record.get("file_hash_sha1"), "sha1"),
            file_hash_sha256=_hash(record.get("file_hash_sha256"), "sha256"),
            domain=_truncate(str(record.get("domain")), FIELD_MAX_LENGTHS["domain"]) if record.get("domain") is not None else None,
            url=_truncate(str(record.get("url")), 2048) if record.get("url") is not None else None,
            cloud_identity=_truncate(str(record.get("cloud_identity")), FIELD_MAX_LENGTHS["cloud_identity"]) if record.get("cloud_identity") is not None else None,
            cloud_resource=_truncate(str(record.get("cloud_resource")), FIELD_MAX_LENGTHS["cloud_resource"]) if record.get("cloud_resource") is not None else None,
            authentication_result=_auth_result(record.get("authentication_result")),
            correlation_key=_truncate(str(record.get("correlation_key")), FIELD_MAX_LENGTHS["correlation_key"]) if record.get("correlation_key") is not None else None,
            session_id=_truncate(str(record.get("session_id")), FIELD_MAX_LENGTHS["session_id"]) if record.get("session_id") is not None else None,
            normalized=payload,
        )


def normalize_generic(payload: dict[str, Any], occurred_at: datetime) -> NormalizedEventRecord:
    """Normalize a generic JSON security event into the canonical model.

    Recognizes the platform's own canonical field names (snake_case) so any
    connector can emit events already in canonical form, and also maps the
    most common vendor field names.
    """

    class GenericNormalizer(ConnectorNormalizer):
        connector_name = "generic"
        field_mapping = {
            # Time
            "occurred_at": "occurred_at",
            "timestamp": "occurred_at",
            "event_time": "occurred_at",
            "time": "occurred_at",
            # Identity
            "user": "username",
            "username": "username",
            "user_name": "username",
            "account": "username",
            "actor": "actor",
            "target": "target",
            "target_user": "target",
            "victim": "target",
            # Network
            "source_ip": "source_ip",
            "src_ip": "source_ip",
            "sourceip": "source_ip",
            "client_ip": "source_ip",
            "source_port": "source_port",
            "src_port": "source_port",
            "destination_ip": "destination_ip",
            "dest_ip": "destination_ip",
            "dst_ip": "destination_ip",
            "destinationip": "destination_ip",
            "destination_port": "destination_port",
            "dest_port": "destination_port",
            "dst_port": "destination_port",
            "protocol": "protocol",
            "network_protocol": "protocol",
            # Endpoint
            "hostname": "hostname",
            "host": "hostname",
            "machine": "hostname",
            "computer": "hostname",
            "process": "process_name",
            "process_name": "process_name",
            "processname": "process_name",
            "command_line": "command_line",
            "commandline": "command_line",
            "cmd": "command_line",
            # Indicators
            "md5": "file_hash_md5",
            "sha1": "file_hash_sha1",
            "sha256": "file_hash_sha256",
            "domain": "domain",
            "url": "url",
            "request_url": "url",
            # Cloud
            "cloud_user": "cloud_identity",
            "cloud_identity": "cloud_identity",
            "cloud_resource": "cloud_resource",
            # Classification
            "event_type": "event_type",
            "event_id": "event_type",
            "category": "event_category",
            "event_category": "event_category",
            "severity": "severity",
            "level": "severity",
            "event_severity": "severity",
            "authentication_result": "authentication_result",
            "auth_result": "authentication_result",
            "result": "authentication_result",
            # Correlation
            "session_id": "session_id",
            "correlation_key": "correlation_key",
        }
        defaults = {"occurred_at": None}

        def derive(self, record: dict[str, Any], payload: dict[str, Any]) -> None:
            # Lift common CSV/header action labels into authentication_result
            # so rule selection blocks like {authentication_result: failure}
            # match events whose payload only carries an `action` column.
            if record.get("authentication_result") is None:
                raw_action = payload.get("action")
                if isinstance(raw_action, str):
                    lowered = raw_action.strip().lower()
                    if lowered in ALLOWED_AUTHENTICATION_RESULTS:
                        record["authentication_result"] = lowered
                    elif "fail" in lowered:
                        record["authentication_result"] = "failure"
                    elif lowered in ("success", "logon", "login", "sign_in", "signin"):
                        record["authentication_result"] = "success"
            if record.get("actor") is None and record.get("username"):
                record["actor"] = record["username"]
            if record.get("event_type") in (None, "generic"):
                inferred_type = payload.get("event_type") or payload.get("event_id") or "generic"
                # CSV/header uploads often label the row action (e.g. failed_login)
                # as an `action` column — lift it into the canonical event_type.
                if inferred_type == "generic" and isinstance(payload.get("action"), str):
                    inferred_type = payload["action"].strip().lower() or "generic"
                record["event_type"] = inferred_type
            if record.get("severity") in (None,):
                raw_severity = payload.get("severity") or payload.get("level")
                if isinstance(raw_severity, int):
                    if raw_severity >= 9:
                        record["severity"] = "critical"
                    elif raw_severity >= 7:
                        record["severity"] = "high"
                    elif raw_severity >= 4:
                        record["severity"] = "medium"
                    elif raw_severity >= 1:
                        record["severity"] = "low"
                    else:
                        record["severity"] = "informational"
            if not record.get("correlation_key"):
                record["correlation_key"] = build_correlation_key(record)

    return GenericNormalizer().normalize(payload, occurred_at)


def build_correlation_key(record: dict[str, Any]) -> str | None:
    """Build a deterministic correlation key from the strongest available
    identity anchors (username, hostname, source IP)."""

    anchors = [
        record.get("username"),
        record.get("hostname"),
        record.get("source_ip"),
    ]
    parts = [str(anchor).lower() for anchor in anchors if anchor]
    return "|".join(parts) if parts else None
