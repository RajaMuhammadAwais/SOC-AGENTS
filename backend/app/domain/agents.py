from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


class AgentName(str, Enum):
    alert_triage = "alert_triage"
    threat_intelligence = "threat_intelligence"
    investigation = "investigation"
    threat_hunting = "threat_hunting"
    risk_scoring = "risk_scoring"
    report_generation = "report_generation"
    response = "response"


@dataclass
class AgentState:
    tenant_id: UUID
    objective: str
    alert_id: UUID | None = None
    incident_id: UUID | None = None
    evidence_ids: list[UUID] = field(default_factory=list)
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    findings: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    requires_approval: bool = False
    next_action: str | None = None
    terminal_status: str | None = None
