from app.agents.report_generation import (
    build_executive_report,
    build_rca_report,
    build_technical_report,
    run_report_generation,
)


def test_build_executive_report_focuses_on_business_decisions() -> None:
    result = build_executive_report(
        {
            "incident_id": "inc-1",
            "title": "Credential attack",
            "risk_level": "high",
            "risk_score": 82,
            "affected_assets": ["vpn", "server-1"],
            "recommendations": ["Approve account reset"],
        }
    )

    assert result["report"]["audience"] == "executive"
    assert result["report"]["business_impact"] == "High risk affecting 2 asset(s)."
    assert result["report"]["recommended_decisions"] == ["Approve account reset"]
    assert result["next_action"] == "review_with_incident_lead"


def test_build_technical_report_includes_timeline_and_evidence() -> None:
    result = build_technical_report(
        {
            "timeline": ["10:00 login", "10:05 rdp"],
            "affected_assets": ["server-1"],
            "findings": ["RDP from unusual source"],
            "recommendations": ["Collect endpoint triage package"],
        }
    )

    assert result["report"]["audience"] == "technical"
    assert result["report"]["timeline"] == ["10:00 login", "10:05 rdp"]
    assert result["report"]["affected_assets"] == ["server-1"]
    assert result["next_action"] == "attach_evidence_and_validate_findings"


def test_build_rca_report_defaults_unknown_root_cause() -> None:
    result = build_rca_report(
        {
            "findings": ["MFA fatigue observed"],
            "recommendations": ["Enforce phishing-resistant MFA"],
        }
    )

    assert result["report"]["audience"] == "post_incident_review"
    assert result["report"]["root_cause"] == "undetermined"
    assert result["report"]["corrective_actions"] == ["Enforce phishing-resistant MFA"]


def test_run_report_generation_routes_report_type() -> None:
    executive = run_report_generation({"report_type": "executive"})
    rca = run_report_generation({"report_type": "rca"})
    default = run_report_generation({})

    assert executive["report"]["audience"] == "executive"
    assert rca["report"]["audience"] == "post_incident_review"
    assert default["report"]["audience"] == "technical"
