"""Tests for the autonomous execution policy engine.

Covers the decision-lane model: skill-level policy always wins, autonomy
levels gate which risk classes may execute without approval, low confidence
escalates, and time-boxed lanes apply for human decision lanes.
"""
from app.domain.models import SkillExecutionPolicy, SkillRiskClass
from app.domain.policy.autonomy import (
    AutonomyLevel,
    PolicyDecision,
    evaluate_autonomy,
)


def _decision(**kwargs):
    return evaluate_autonomy(
        skill_risk_class=kwargs.get("risk", SkillRiskClass.low),
        skill_policy=kwargs.get("policy", SkillExecutionPolicy.allow),
        autonomy_level=kwargs.get("level", AutonomyLevel.l3_guarded),
        confidence=kwargs.get("confidence"),
        confidence_floor=kwargs.get("floor", 0.0),
    )


def test_deny_policy_never_executes() -> None:
    result = _decision(policy=SkillExecutionPolicy.deny, risk=SkillRiskClass.informational, level=AutonomyLevel.l4_autonomous)
    assert result.decision == PolicyDecision.deny
    assert result.lane_seconds is None


def test_require_approval_policy_uses_risk_lane() -> None:
    result = _decision(policy=SkillExecutionPolicy.require_approval, risk=SkillRiskClass.elevated, level=AutonomyLevel.l4_autonomous)
    assert result.decision == PolicyDecision.require_approval
    assert result.lane_seconds == 120


def test_critical_risk_on_guarded_escapes_to_human_lane() -> None:
    result = _decision(risk=SkillRiskClass.critical, level=AutonomyLevel.l3_guarded)
    assert result.decision == PolicyDecision.require_approval
    assert result.lane_seconds == 300


def test_informational_risk_on_supervised_allows() -> None:
    result = _decision(risk=SkillRiskClass.informational, level=AutonomyLevel.l2_supervised)
    assert result.decision == PolicyDecision.allow


def test_low_risk_on_supervised_requires_approval() -> None:
    result = _decision(risk=SkillRiskClass.low, level=AutonomyLevel.l2_supervised)
    assert result.decision == PolicyDecision.require_approval


def test_advisory_level_never_allows_autonomy() -> None:
    for risk in SkillRiskClass:
        result = _decision(risk=risk, level=AutonomyLevel.l1_advisory)
        assert result.decision == PolicyDecision.require_approval, f"{risk} should not be autonomous at L1"


def test_low_confidence_escapes_to_human_lane() -> None:
    result = _decision(risk=SkillRiskClass.low, level=AutonomyLevel.l4_autonomous, confidence=0.45, floor=0.7)
    assert result.decision == PolicyDecision.require_approval


def test_high_confidence_at_guarded_level_allows() -> None:
    result = _decision(risk=SkillRiskClass.low, level=AutonomyLevel.l3_guarded, confidence=0.9, floor=0.7)
    assert result.decision == PolicyDecision.allow


def test_guarded_level_allows_informational_and_low() -> None:
    for risk in (SkillRiskClass.informational, SkillRiskClass.low):
        result = _decision(risk=risk, level=AutonomyLevel.l3_guarded)
        assert result.decision == PolicyDecision.allow, f"{risk} should be autonomous at L3"


def test_autonomous_level_allows_elevated() -> None:
    result = _decision(risk=SkillRiskClass.elevated, level=AutonomyLevel.l4_autonomous)
    assert result.decision == PolicyDecision.allow


def test_manual_level_denies_all_autonomy() -> None:
    result = _decision(risk=SkillRiskClass.informational, level=AutonomyLevel.l0_manual)
    assert result.decision == PolicyDecision.require_approval
