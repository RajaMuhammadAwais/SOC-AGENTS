from app.agents.supervisor import route_soc_work


def test_supervisor_routes_response_before_investigation() -> None:
    result = route_soc_work(
        {
            "objective": "Investigate and isolate endpoint",
            "severity": "critical",
            "has_incident": True,
        }
    )

    assert result["selected_agent"] == "response"
    assert result["priority"] == "critical"
    assert result["next_action"] == "request_approval_or_execute_response"
    assert result["requires_human_review"] is True


def test_supervisor_routes_incident_to_investigation() -> None:
    result = route_soc_work(
        {
            "objective": "Build attack timeline",
            "severity": "high",
            "has_incident": True,
        }
    )

    assert result["selected_agent"] == "investigation"
    assert result["priority"] == "high"


def test_supervisor_routes_observable_to_threat_intelligence() -> None:
    result = route_soc_work(
        {
            "objective": "Check CVE and hash reputation",
            "has_observable": True,
        }
    )

    assert result["selected_agent"] == "threat_intelligence"
    assert result["next_action"] == "enrich_observable"


def test_supervisor_validates_low_confidence_response_before_action() -> None:
    result = route_soc_work(
        {
            "objective": "Block suspicious source immediately",
            "severity": "high",
            "confidence": 0.2,
            "has_alert": True,
        }
    )

    assert result["selected_agent"] == "alert_triage"
    assert result["priority"] == "high"
    assert result["next_action"] == "validate_alert_before_response"
    assert result["requires_human_review"] is True


def test_supervisor_routes_report_when_evidence_is_ready() -> None:
    result = route_soc_work(
        {
            "objective": "Write executive summary for incident",
            "severity": "medium",
            "has_incident": True,
            "has_evidence": True,
        }
    )

    assert result["selected_agent"] == "report_generation"
    assert result["next_action"] == "generate_report"


def test_supervisor_collects_context_for_risk_score_without_case_context() -> None:
    result = route_soc_work({"objective": "Score business impact"})

    assert result["selected_agent"] == "risk_scoring"
    assert result["next_action"] == "collect_context_for_risk_score"


def test_supervisor_defaults_to_alert_triage() -> None:
    result = route_soc_work({"objective": "New EDR alert", "severity": "medium"})

    assert result["selected_agent"] == "alert_triage"
    assert result["priority"] == "medium"
    assert result["rationale"] == "Defaulting to alert triage for initial SOC assessment."
