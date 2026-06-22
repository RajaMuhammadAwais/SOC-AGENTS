from typing import TypedDict


class RiskScoringState(TypedDict, total=False):
    severity: str
    confidence: float
    cvss_score: float
    asset_criticality: str
    data_sensitivity: str
    affected_assets_count: int
    internet_exposed: bool
    exploit_available: bool
    active_exploitation: bool
    duplicate_count: int
    likelihood_score: int
    impact_score: int
    risk_score: int
    risk_level: str
    explanation: list[str]
    decision_factors: list[str]
    human_review_required: bool
    response_urgency: str
    recommended_action: str


def calculate_likelihood_score(state: RiskScoringState) -> RiskScoringState:
    severity = state.get("severity", "medium").lower()
    score = {
        "critical": 80,
        "high": 65,
        "medium": 45,
        "low": 25,
        "informational": 10,
    }.get(severity, 45)
    explanation = [f"Severity contributes a {score} likelihood baseline."]

    if state.get("active_exploitation"):
        score += 15
        explanation.append("Active exploitation increases likelihood.")
    if state.get("exploit_available"):
        score += 10
        explanation.append("Public exploit availability increases likelihood.")
    if state.get("internet_exposed"):
        score += 10
        explanation.append("Internet exposure increases likelihood.")
    if state.get("duplicate_count", 0) >= 5:
        score += 5
        explanation.append("Repeated matching alerts increase likelihood.")

    confidence = state.get("confidence", 0.5)
    if confidence >= 0.8:
        score += 5
        explanation.append("High signal confidence increases likelihood.")
    elif confidence < 0.4:
        score -= 10
        explanation.append("Low signal confidence reduces likelihood.")

    return {
        "likelihood_score": _clamp_score(score),
        "explanation": explanation,
    }


def calculate_impact_score(state: RiskScoringState) -> RiskScoringState:
    criticality = state.get("asset_criticality", "medium").lower()
    score = {
        "critical": 85,
        "high": 70,
        "medium": 50,
        "low": 25,
    }.get(criticality, 50)
    explanation = [f"Asset criticality contributes a {score} impact baseline."]

    sensitivity = state.get("data_sensitivity", "medium").lower()
    if sensitivity in {"regulated", "restricted"}:
        score += 15
        explanation.append("Regulated or restricted data increases impact.")
    elif sensitivity == "high":
        score += 10
        explanation.append("High data sensitivity increases impact.")

    affected_assets_count = state.get("affected_assets_count", 1)
    if affected_assets_count > 1:
        increase = min(affected_assets_count * 3, 15)
        score += increase
        explanation.append(f"{affected_assets_count} affected assets increase impact.")

    cvss_score = state.get("cvss_score", 0)
    if cvss_score >= 9:
        score += 10
        explanation.append("Critical CVSS severity increases technical impact.")
    elif cvss_score >= 7:
        score += 5
        explanation.append("High CVSS severity increases technical impact.")

    return {
        "impact_score": _clamp_score(score),
        "explanation": explanation,
    }


def calculate_risk_score(state: RiskScoringState) -> RiskScoringState:
    likelihood = state.get("likelihood_score", 45)
    impact = state.get("impact_score", 50)
    score = _clamp_score(round(likelihood * 0.45 + impact * 0.55))
    level = map_risk_level(score)
    decision_factors = _decision_factors(state, score, level)
    return {
        "risk_score": score,
        "risk_level": level,
        "decision_factors": decision_factors,
        "human_review_required": _human_review_required(state, score, level),
        "response_urgency": _response_urgency(level),
        "recommended_action": _recommended_action(level),
    }


def run_risk_scoring(state: RiskScoringState) -> RiskScoringState:
    current: RiskScoringState = {**state}
    likelihood = calculate_likelihood_score(current)
    current.update(likelihood)

    impact = calculate_impact_score(current)
    current.update(
        {
            "impact_score": impact["impact_score"],
            "explanation": likelihood["explanation"] + impact["explanation"],
        }
    )

    current.update(calculate_risk_score(current))
    return current


def map_risk_level(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    if score >= 20:
        return "low"
    return "informational"


def _recommended_action(level: str) -> str:
    return {
        "critical": "contain_immediately_and_notify_leadership",
        "high": "prioritize_response_and_open_incident",
        "medium": "investigate_during_current_queue",
        "low": "monitor_and_tune_detection",
        "informational": "record_for_context",
    }[level]


def _decision_factors(state: RiskScoringState, score: int, level: str) -> list[str]:
    factors = [f"weighted_score={score}", f"risk_level={level}"]
    if state.get("active_exploitation"):
        factors.append("active_exploitation")
    if state.get("internet_exposed"):
        factors.append("internet_exposed_asset")
    if state.get("data_sensitivity", "").lower() in {"regulated", "restricted", "high"}:
        factors.append("sensitive_data")
    if state.get("confidence", 0.5) < 0.45:
        factors.append("low_confidence")
    return factors


def _human_review_required(state: RiskScoringState, score: int, level: str) -> bool:
    if level in {"critical", "high"}:
        return True
    low_confidence = state.get("confidence", 0.5) < 0.45
    if state.get("severity", "medium").lower() in {"critical", "high"} and low_confidence:
        return True
    return score >= 60 and low_confidence


def _response_urgency(level: str) -> str:
    if level == "critical":
        return "immediate"
    if level == "high":
        return "same_shift"
    if level == "medium":
        return "current_queue"
    return "routine"


def _clamp_score(value: int) -> int:
    return max(0, min(value, 100))
