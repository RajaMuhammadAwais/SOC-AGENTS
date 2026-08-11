"""Autonomy policy engine for human-out-of-the-loop agent execution.

Implements the decision-lane model from the SOC autonomy design:
- The oversight level is a property of the *decision*, not of the agent:
  every skill execution request is evaluated against the skill's risk class,
  the tenant's autonomy maturity level, and an optional confidence floor.
- Deterministic policy result: `allow` (autonomous execution, fully audited),
  `require_approval` (route to a human decision lane with a time-box), or
  `deny` (refuse autonomous execution; analyst must act manually).
- Time-boxed decision lanes with fail-safe-deny on timeout.

Reference design sources:
- Strata, "Human-in-the-Loop: A 2026 Guide" (decision lanes, fail-safe-deny)
- Elementum, "Human-in-the-Loop Agentic AI" (HITL/HOTL/HOOTL spectrum)
- CoALA memory taxonomy (procedural memory = skill registry)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from app.domain.models import SkillExecutionPolicy, SkillRiskClass


class AutonomyLevel(StrEnum):
    """Tenant autonomy maturity level. Higher levels unlock lower-risk
    autonomous execution without human approval.

    L0 = manual: all actions require explicit analyst execution.
    L1 = advisory: agents recommend; analysts execute (no autonomy).
    L2 = supervised: low-risk autonomous execution allowed (HOTL audit trail).
    L3 = guarded: low + elevated (reversible) autonomous execution allowed.
    L4 = autonomous: all policy-allow skills execute without approval,
         but every action is audit-logged and rate-limited.
    """

    l0_manual = "l0_manual"
    l1_advisory = "l1_advisory"
    l2_supervised = "l2_supervised"
    l3_guarded = "l3_guarded"
    l4_autonomous = "l4_autonomous"


class PolicyDecision(StrEnum):
    allow = "allow"
    require_approval = "require_approval"
    deny = "deny"


@dataclass(frozen=True)
class AutonomyDecision:
    decision: PolicyDecision
    reason: str
    lane_seconds: int | None = None  # decision-lane time-box (seconds), None when not applicable


# Lane durations per risk class, in seconds (Strata time-boxed decision lanes).
LANE_DURATIONS: dict[SkillRiskClass, int] = {
    SkillRiskClass.informational: 0,  # no human wait; audit only
    SkillRiskClass.low: 60,
    SkillRiskClass.elevated: 120,
    SkillRiskClass.critical: 300,
}


# Risk classes each autonomy level may execute without approval.
AUTONOMOUS_RISK_CLASSES: dict[AutonomyLevel, set[SkillRiskClass]] = {
    AutonomyLevel.l0_manual: set(),
    AutonomyLevel.l1_advisory: set(),
    AutonomyLevel.l2_supervised: {SkillRiskClass.informational},
    AutonomyLevel.l3_guarded: {SkillRiskClass.informational, SkillRiskClass.low},
    AutonomyLevel.l4_autonomous: {
        SkillRiskClass.informational,
        SkillRiskClass.low,
        SkillRiskClass.elevated,
    },
}


def evaluate_autonomy(
    *,
    skill_risk_class: SkillRiskClass,
    skill_policy: SkillExecutionPolicy,
    autonomy_level: AutonomyLevel,
    confidence: float | None = None,
    confidence_floor: float = 0.0,
) -> AutonomyDecision:
    """Deterministic evaluation of whether a skill may execute autonomously.

    Rules (evaluated in order):
    1. Skill-level policy always wins: `deny` never executes; `require_approval`
       always routes to a human lane; `allow` defers to the autonomy level.
    2. At L0/L1 no autonomous execution is permitted regardless of risk class.
    3. The skill's risk class must be within the autonomy level's allow-set.
    4. If a confidence score is provided it must meet the floor; uncertain
       detections always escalate to a human lane (fail-safe principle).
    """
    if skill_policy == SkillExecutionPolicy.deny:
        return AutonomyDecision(
            PolicyDecision.deny,
            "Skill is explicitly denied for autonomous execution by its policy.",
        )
    if skill_policy == SkillExecutionPolicy.require_approval:
        return AutonomyDecision(
            PolicyDecision.require_approval,
            f"Skill {skill_risk_class.value}-risk requires analyst approval (lane {LANE_DURATIONS[skill_risk_class]}s).",
            lane_seconds=LANE_DURATIONS[skill_risk_class],
        )

    if autonomy_level in (AutonomyLevel.l0_manual, AutonomyLevel.l1_advisory):
        return AutonomyDecision(
            PolicyDecision.require_approval,
            f"Autonomy level {autonomy_level.value} does not permit autonomous execution.",
        )

    if skill_risk_class not in AUTONOMOUS_RISK_CLASSES[autonomy_level]:
        return AutonomyDecision(
            PolicyDecision.require_approval,
            (
                f"Risk class {skill_risk_class.value} exceeds autonomy level "
                f"{autonomy_level.value} (max autonomous: "
                + ", ".join(sorted(rc.value for rc in AUTONOMOUS_RISK_CLASSES[autonomy_level]))
                + ")."
            ),
            lane_seconds=LANE_DURATIONS[skill_risk_class],
        )

    if confidence is not None and confidence < confidence_floor:
        return AutonomyDecision(
            PolicyDecision.require_approval,
            (
                f"Confidence {confidence:.2f} below floor {confidence_floor:.2f}; "
                "escalating to analyst decision lane."
            ),
            lane_seconds=LANE_DURATIONS[skill_risk_class],
        )

    return AutonomyDecision(
        PolicyDecision.allow,
        f"Autonomous execution permitted at {autonomy_level.value} for {skill_risk_class.value}-risk skill.",
        lane_seconds=None,
    )


def decision_lane_timedelta(seconds: int | None) -> timedelta | None:
    return timedelta(seconds=seconds) if seconds else None
