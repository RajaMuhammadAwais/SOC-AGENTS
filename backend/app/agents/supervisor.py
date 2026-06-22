from typing import TypedDict

from app.domain.agents import AgentName

Severity = str


class SupervisorState(TypedDict, total=False):
    objective: str
    severity: str
    confidence: float
    has_alert: bool
    has_incident: bool
    has_observable: bool
    has_evidence: bool
    requires_response: bool
    selected_agent: str
    priority: str
    rationale: str
    next_action: str
    requires_human_review: bool
    routing_notes: list[str]


def route_soc_work(state: SupervisorState) -> SupervisorState:
    objective = _normalize_text(state.get("objective", ""))
    severity = _normalize_severity(state.get("severity", "medium"))
    confidence = _normalize_confidence(state.get("confidence"))
    has_context = any(
        (
            state.get("has_incident", False),
            state.get("has_alert", False),
            state.get("has_observable", False),
            state.get("has_evidence", False),
        )
    )
    has_investigation_context = any(
        (
            state.get("has_incident", False),
            state.get("has_evidence", False),
        )
    )
    notes = _routing_notes(state, severity, confidence)

    if state.get("requires_response") or _contains_any(objective, ("contain", "block", "isolate")):
        if confidence < 0.5 and not has_investigation_context:
            return _decision(
            AgentName.alert_triage,
            _priority_from_severity(severity),
            (
                "Containment intent is present, but the signal needs "
                "analyst-style validation first."
            ),
            "validate_alert_before_response",
            requires_human_review=True,
            routing_notes=notes,
        )
        return _decision(
            AgentName.response,
            "critical" if severity == "critical" else "high",
            "Response requested or containment language is present.",
            "request_approval_or_execute_response",
            requires_human_review=True,
            routing_notes=notes,
        )
    if _contains_any(objective, ("report", "executive", "summary", "rca")) and state.get(
        "has_evidence"
    ):
        return _decision(
            AgentName.report_generation,
            "low",
            "Reporting intent is present and evidence is available.",
            "generate_report",
            routing_notes=notes,
        )
    if _contains_any(objective, ("risk", "score", "impact")) and has_context:
        return _decision(
            AgentName.risk_scoring,
            _priority_from_severity(severity),
            "Risk-scoring intent is present with enough context to estimate impact.",
            "calculate_risk_score",
            routing_notes=notes,
        )
    if state.get("has_incident") or _contains_any(
        objective,
        ("investigate", "timeline", "root cause", "scope", "evidence"),
    ):
        return _decision(
            AgentName.investigation,
            _priority_from_severity(severity),
            "Incident context or investigation intent is present.",
            "build_timeline_and_scope_assets",
            routing_notes=notes,
        )
    if state.get("has_observable") or _contains_any(
        objective,
        ("ioc", "cve", "reputation", "hash", "domain", "url"),
    ):
        return _decision(
            AgentName.threat_intelligence,
            "medium",
            "Observable or threat-intelligence intent is present.",
            "enrich_observable",
            routing_notes=notes,
        )
    if _contains_any(objective, ("hunt", "similar", "hidden")):
        return _decision(
            AgentName.threat_hunting,
            "medium",
            "Threat-hunting intent is present.",
            "search_for_similar_activity",
            routing_notes=notes,
        )
    if _contains_any(objective, ("risk", "score", "impact")):
        return _decision(
            AgentName.risk_scoring,
            "medium",
            "Risk-scoring intent is present, but more context may be needed.",
            "collect_context_for_risk_score",
            routing_notes=notes,
        )
    if _contains_any(objective, ("report", "executive", "summary", "rca")):
        return _decision(
            AgentName.report_generation,
            "low",
            "Reporting intent is present, but evidence should be gathered before finalizing.",
            "collect_evidence_for_report",
            routing_notes=notes,
        )
    return _decision(
        AgentName.alert_triage,
        _priority_from_severity(severity),
        "Defaulting to alert triage for initial SOC assessment.",
        "triage_alert",
        routing_notes=notes,
    )


def _decision(
    agent: AgentName,
    priority: str,
    rationale: str,
    next_action: str,
    *,
    requires_human_review: bool = False,
    routing_notes: list[str] | None = None,
) -> SupervisorState:
    decision: SupervisorState = {
        "selected_agent": agent.value,
        "priority": priority,
        "rationale": rationale,
        "next_action": next_action,
    }
    if requires_human_review:
        decision["requires_human_review"] = True
    if routing_notes:
        decision["routing_notes"] = routing_notes
    return decision


def _priority_from_severity(severity: Severity) -> str:
    if severity in {"critical", "high"}:
        return "high"
    if severity in {"informational", "low"}:
        return "low"
    return "medium"


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _normalize_severity(severity: str) -> Severity:
    normalized = severity.lower().strip()
    if normalized in {"critical", "high", "medium", "low", "informational"}:
        return normalized
    return "medium"


def _normalize_confidence(confidence: float | None) -> float:
    if confidence is None:
        return 0.75
    return max(0.0, min(confidence, 1.0))


def _routing_notes(state: SupervisorState, severity: Severity, confidence: float) -> list[str]:
    notes: list[str] = [f"severity={severity}", f"confidence={confidence:.2f}"]
    if state.get("has_alert"):
        notes.append("alert_context")
    if state.get("has_incident"):
        notes.append("incident_context")
    if state.get("has_observable"):
        notes.append("observable_context")
    if state.get("has_evidence"):
        notes.append("evidence_context")
    return notes


def _contains_any(value: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in value for keyword in keywords)
