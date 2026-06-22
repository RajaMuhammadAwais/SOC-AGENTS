from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class PageInfo(BaseModel):
    next_cursor: str | None = None


class CursorPage[T](BaseModel):
    items: list[T]
    page: PageInfo = Field(default_factory=PageInfo)


class LoginRequest(BaseModel):
    tenant_slug: str = Field(min_length=2, max_length=120)
    email: str
    password: str
    mfa_code: str | None = None


class RegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=255)
    tenant_slug: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class MfaSetupResponse(BaseModel):
    secret: str
    recovery_codes: list[str]


class MfaVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=64)


class MfaStatusResponse(BaseModel):
    is_mfa_enabled: bool


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32)


class PrincipalResponse(BaseModel):
    user_id: str
    tenant_id: str
    permissions: list[str]


class AlertSummary(BaseModel):
    id: UUID
    title: str
    severity: str
    status: str
    source: str
    created_at: datetime


class AlertCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str | None = None
    severity: Literal["informational", "low", "medium", "high", "critical"]
    source: str = Field(min_length=2, max_length=120)
    risk_score: int | None = Field(default=None, ge=0, le=100)
    mitre: dict[str, Any] = Field(default_factory=dict)


class AlertUpdate(BaseModel):
    status: Literal["new", "triaged", "investigating", "false_positive", "closed"] | None = None
    severity: Literal["informational", "low", "medium", "high", "critical"] | None = None
    risk_score: int | None = Field(default=None, ge=0, le=100)


class IncidentSummary(BaseModel):
    id: UUID
    title: str
    severity: str
    status: str
    updated_at: datetime


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    summary: str | None = None
    severity: Literal["informational", "low", "medium", "high", "critical"]
    alert_ids: list[UUID] = Field(default_factory=list)


class InvestigationSummary(BaseModel):
    id: UUID
    incident_id: UUID
    title: str
    status: str
    updated_at: datetime


class InvestigationCreate(BaseModel):
    incident_id: UUID
    title: str = Field(min_length=3, max_length=255)


class ObservableSummary(BaseModel):
    id: UUID
    type: str
    value: str
    created_at: datetime


class ObservableCreate(BaseModel):
    type: str = Field(min_length=2, max_length=80)
    value: str = Field(min_length=1)


class ReportSummary(BaseModel):
    id: UUID
    incident_id: UUID
    report_type: str
    status: str
    updated_at: datetime


class ReportCreate(BaseModel):
    incident_id: UUID
    report_type: Literal["executive", "technical", "rca", "compliance"]


class UserSummary(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=256)


class RoleSummary(BaseModel):
    id: UUID
    name: str
    description: str | None = None


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class AssignRoleRequest(BaseModel):
    user_id: UUID
    role_id: UUID


class RawEventIngestRequest(BaseModel):
    data_source_id: UUID
    source_event_id: str = Field(min_length=1, max_length=512)
    occurred_at: datetime
    payload: dict[str, Any]


class NormalizedEventSummary(BaseModel):
    id: UUID
    event_type: str
    occurred_at: datetime
    actor: str | None = None
    target: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None


class AgentRunRequest(BaseModel):
    alert_id: UUID | None = None
    incident_id: UUID | None = None
    objective: str = Field(min_length=3, max_length=1000)


class AgentRunResponse(BaseModel):
    run_id: UUID
    status: str


class AgentRunSummary(BaseModel):
    id: UUID
    agent_name: str
    status: str
    created_at: datetime


class AgentTriagePreviewResponse(BaseModel):
    severity: str
    category: str
    confidence: float = Field(ge=0, le=1)
    rationale: str
    next_action: str
