from __future__ import annotations

import enum
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class Severity(str, enum.Enum):
    informational = "informational"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    new = "new"
    triaged = "triaged"
    investigating = "investigating"
    false_positive = "false_positive"
    closed = "closed"


class IncidentStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    contained = "contained"
    resolved = "resolved"
    closed = "closed"


class AgentRunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    waiting_for_approval = "waiting_for_approval"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ResponseActionStatus(str, enum.Enum):
    recommended = "recommended"
    awaiting_approval = "awaiting_approval"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"
    failed = "failed"


class Tenant(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list[User]] = relationship(back_populates="tenant")


class User(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("ix_users_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(128))
    mfa_recovery_codes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="users")
    role_assignments: Mapped[list[UserRole]] = relationship(back_populates="user")


class Role(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    permissions: Mapped[list[RolePermission]] = relationship(back_populates="role")
    user_assignments: Mapped[list[UserRole]] = relationship(back_populates="role")


class Permission(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class RolePermission(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[UUID] = mapped_column(ForeignKey("permissions.id"), nullable=False)

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship()


class UserRole(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)

    user: Mapped[User] = relationship(back_populates="role_assignments")
    role: Mapped[Role] = relationship(back_populates="user_assignments")


class ApiKey(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_keys"
    __table_args__ = (Index("ix_api_keys_tenant_id", "tenant_id"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    scopes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Asset(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_tenant_type", "tenant_id", "asset_type"),
        UniqueConstraint("tenant_id", "external_id", name="uq_assets_tenant_external_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255))
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class DataSource(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_sources"
    __table_args__ = (Index("ix_data_sources_tenant_id", "tenant_id"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(120), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RawEvent(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "raw_events"
    __table_args__ = (
        Index("ix_raw_events_tenant_occurred", "tenant_id", "occurred_at"),
        UniqueConstraint("tenant_id", "source_event_id", name="uq_raw_events_tenant_source_event"),
    )

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    data_source_id: Mapped[UUID] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(512), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class NormalizedEvent(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "normalized_events"
    __table_args__ = (Index("ix_normalized_events_tenant_occurred", "tenant_id", "occurred_at"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    raw_event_id: Mapped[UUID] = mapped_column(ForeignKey("raw_events.id"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255))
    target: Mapped[str | None] = mapped_column(String(255))
    source_ip: Mapped[str | None] = mapped_column(String(64))
    destination_ip: Mapped[str | None] = mapped_column(String(64))
    normalized: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Alert(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_tenant_status_severity", "tenant_id", "status", "severity"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus),
        default=AlertStatus.new,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    mitre: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Incident(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incidents_tenant_status_severity", "tenant_id", "status", "severity"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus),
        default=IncidentStatus.open,
        nullable=False,
    )
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class IncidentAlert(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "incident_alerts"
    __table_args__ = (
        UniqueConstraint("incident_id", "alert_id", name="uq_incident_alerts_incident_alert"),
    )

    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    alert_id: Mapped[UUID] = mapped_column(ForeignKey("alerts.id"), nullable=False)


class Observable(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "observables"
    __table_args__ = (Index("ix_observables_tenant_type_hash", "tenant_id", "type", "value_hash"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_hash: Mapped[str] = mapped_column(String(128), nullable=False)


class ThreatIntelEnrichment(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "threat_intel_enrichments"
    __table_args__ = (Index("ix_ti_enrichments_observable", "observable_id", "created_at"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    observable_id: Mapped[UUID] = mapped_column(ForeignKey("observables.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    reputation: Mapped[str | None] = mapped_column(String(80))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Investigation(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "investigations"
    __table_args__ = (Index("ix_investigations_tenant_incident", "tenant_id", "incident_id"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="open")
    findings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class InvestigationEvidence(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "investigation_evidence"
    __table_args__ = (Index("ix_investigation_evidence_investigation", "investigation_id"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    investigation_id: Mapped[UUID] = mapped_column(ForeignKey("investigations.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    citation: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class AgentRun(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_tenant_incident_status", "tenant_id", "incident_id", "status"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    incident_id: Mapped[UUID | None] = mapped_column(ForeignKey("incidents.id"))
    alert_id: Mapped[UUID | None] = mapped_column(ForeignKey("alerts.id"))
    investigation_id: Mapped[UUID | None] = mapped_column(ForeignKey("investigations.id"))
    agent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[AgentRunStatus] = mapped_column(Enum(AgentRunStatus), nullable=False)
    model: Mapped[str | None] = mapped_column(String(160))
    graph_thread_id: Mapped[str | None] = mapped_column(String(255))
    token_usage: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    trace: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class AgentStep(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_steps"
    __table_args__ = (Index("ix_agent_steps_run", "agent_run_id", "created_at"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    agent_run_id: Mapped[UUID] = mapped_column(ForeignKey("agent_runs.id"), nullable=False)
    node_name: Mapped[str] = mapped_column(String(160), nullable=False)
    input_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    output_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    tool_calls: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class ResponseAction(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "response_actions"
    __table_args__ = (Index("ix_response_actions_tenant_incident_status", "tenant_id", "incident_id", "status"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ResponseActionStatus] = mapped_column(Enum(ResponseActionStatus), nullable=False)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class Report(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_tenant_incident", "tenant_id", "incident_id"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="draft")
    content: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    citations: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)


class AuditLog(UuidPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_tenant_created_actor", "tenant_id", "created_at", "actor_user_id"),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
