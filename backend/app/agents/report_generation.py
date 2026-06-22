from typing import TypedDict


class ReportState(TypedDict, total=False):
    report_type: str
    incident_id: str
    title: str
    summary: str
    risk_level: str
    risk_score: int
    affected_assets: list[str]
    timeline: list[str]
    findings: list[str]
    recommendations: list[str]
    root_cause: str
    citations: list[str]
    report: dict[str, object]
    next_action: str


def build_executive_report(state: ReportState) -> ReportState:
    report = _base_report(state)
    report.update(
        {
            "audience": "executive",
            "business_impact": _business_impact(state),
            "priority": state.get("risk_level", "medium"),
            "recommended_decisions": state.get("recommendations", []),
        }
    )
    return {"report": report, "next_action": "review_with_incident_lead"}


def build_technical_report(state: ReportState) -> ReportState:
    report = _base_report(state)
    report.update(
        {
            "audience": "technical",
            "timeline": state.get("timeline", []),
            "affected_assets": state.get("affected_assets", []),
            "findings": state.get("findings", []),
            "recommended_actions": state.get("recommendations", []),
        }
    )
    return {"report": report, "next_action": "attach_evidence_and_validate_findings"}


def build_rca_report(state: ReportState) -> ReportState:
    report = _base_report(state)
    report.update(
        {
            "audience": "post_incident_review",
            "root_cause": state.get("root_cause", "undetermined"),
            "contributing_factors": state.get("findings", []),
            "corrective_actions": state.get("recommendations", []),
        }
    )
    return {"report": report, "next_action": "assign_corrective_action_owners"}


def run_report_generation(state: ReportState) -> ReportState:
    report_type = state.get("report_type", "technical").lower()
    if report_type == "executive":
        return {**state, **build_executive_report(state)}
    if report_type in {"rca", "root_cause"}:
        return {**state, **build_rca_report(state)}
    return {**state, **build_technical_report(state)}


def _base_report(state: ReportState) -> dict[str, object]:
    return {
        "incident_id": state.get("incident_id", ""),
        "title": state.get("title", "Security incident report"),
        "summary": state.get("summary", ""),
        "risk": {
            "level": state.get("risk_level", "medium"),
            "score": state.get("risk_score", 0),
        },
        "citations": state.get("citations", []),
    }


def _business_impact(state: ReportState) -> str:
    affected_assets = state.get("affected_assets", [])
    risk_level = state.get("risk_level", "medium")
    if not affected_assets:
        return f"{risk_level.title()} risk with no confirmed affected assets yet."
    return f"{risk_level.title()} risk affecting {len(affected_assets)} asset(s)."
