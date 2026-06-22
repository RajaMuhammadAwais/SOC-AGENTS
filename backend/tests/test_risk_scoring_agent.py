from app.agents.risk_scoring import (
    calculate_impact_score,
    calculate_likelihood_score,
    map_risk_level,
    run_risk_scoring,
)


def test_calculate_likelihood_uses_threat_context() -> None:
    result = calculate_likelihood_score(
        {
            "severity": "high",
            "confidence": 0.9,
            "active_exploitation": True,
            "exploit_available": True,
            "internet_exposed": True,
            "duplicate_count": 5,
        }
    )

    assert result["likelihood_score"] == 100
    assert "Active exploitation increases likelihood." in result["explanation"]


def test_calculate_likelihood_reduces_low_confidence_signals() -> None:
    result = calculate_likelihood_score({"severity": "medium", "confidence": 0.2})

    assert result["likelihood_score"] == 35


def test_calculate_impact_uses_asset_and_vulnerability_context() -> None:
    result = calculate_impact_score(
        {
            "asset_criticality": "high",
            "data_sensitivity": "regulated",
            "affected_assets_count": 4,
            "cvss_score": 9.8,
        }
    )

    assert result["impact_score"] == 100
    assert "Critical CVSS severity increases technical impact." in result["explanation"]


def test_map_risk_level_boundaries() -> None:
    assert map_risk_level(95) == "critical"
    assert map_risk_level(70) == "high"
    assert map_risk_level(40) == "medium"
    assert map_risk_level(20) == "low"
    assert map_risk_level(10) == "informational"


def test_run_risk_scoring_returns_score_level_and_recommendation() -> None:
    result = run_risk_scoring(
        {
            "severity": "high",
            "confidence": 0.85,
            "asset_criticality": "critical",
            "data_sensitivity": "high",
            "internet_exposed": True,
            "cvss_score": 8.1,
        }
    )

    assert result["likelihood_score"] == 80
    assert result["impact_score"] == 100
    assert result["risk_score"] == 91
    assert result["risk_level"] == "critical"
    assert result["human_review_required"] is True
    assert result["response_urgency"] == "immediate"
    assert "internet_exposed_asset" in result["decision_factors"]
    assert result["recommended_action"] == "contain_immediately_and_notify_leadership"


def test_run_risk_scoring_marks_low_confidence_medium_risk_for_review() -> None:
    result = run_risk_scoring(
        {
            "severity": "high",
            "confidence": 0.3,
            "asset_criticality": "medium",
        }
    )

    assert result["risk_level"] == "medium"
    assert result["human_review_required"] is True
    assert "low_confidence" in result["decision_factors"]
    assert result["response_urgency"] == "current_queue"
