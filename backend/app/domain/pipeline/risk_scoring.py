"""Deterministic, reproducible risk scoring model.

Score = asset_severity_score + attacker_progress_score + asset_criticality_score
bounded to [0, 1000]. Every component is a pure function of observable event
attributes and asset metadata; no LLM output influences the numeric score,
so identical inputs always produce identical scores (reproducibility
requirement). The agent layer may add narrative context on top, but never
alters this base score.

Documented per spec section "Risk Scoring Agent — must be
deterministic/reproducible where possible; document the scoring model."

    Component 1 — Asset severity (0-400)
        Derived from the alert/normalized event severity:
        critical=400, high=300, medium=200, low=100, informational=0

    Component 2 — Attacker progress (0-300)
        Derived from MITRE ATT&CK tactic coverage observed in the alert's
        rule metadata and related events. Tactic progression indicates the
        attack has moved beyond initial access:
        initial_access only            = 100
        + execution/privilege_escalation = +100
        + lateral_movement/persistence = +50
        + exfiltration/impact          = +50 (max 300)

    Component 3 — Asset criticality (0-300)
        Derived from asset metadata (asset.attributes.criticality or a
        default medium=150):
        critical=300, high=250, medium=150, low=50, unknown=150

Confidence is computed separately as the ratio of verified evidence fields
(0.0-1.0) and is reported alongside the score; it never scales the score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.models import Severity

TACTIC_PROGRESS_WEIGHTS = {
    "initial_access": 100,
    "execution": 100,
    "privilege_escalation": 100,
    "defense_evasion": 0,
    "credential_access": 100,
    "discovery": 50,
    "lateral_movement": 150,
    "collection": 100,
    "command_and_control": 100,
    "exfiltration": 200,
    "impact": 200,
    "persistence": 150,
}

SEVERITY_SCORES = {
    Severity.informational: 0,
    Severity.low: 100,
    Severity.medium: 200,
    Severity.high: 300,
    Severity.critical: 400,
}

ASSET_CRITICALITY_SCORES = {
    "critical": 300,
    "high": 250,
    "medium": 150,
    "low": 50,
    "unknown": 150,
}

MAX_SCORE = 1000


@dataclass(frozen=True)
class RiskAssessment:
    risk_score: int
    severity: Severity
    confidence: float
    asset_score: int
    progress_score: int
    criticality_score: int
    tactic_coverage: list[str]
    explanation: str


def compute_risk_score(
    severity: Severity,
    mitre_tactics: list[str],
    asset_criticality: str | None = None,
    evidence_field_count: int = 0,
    total_evidence_fields: int = 1,
) -> RiskAssessment:
    """Pure deterministic scoring function (unit testable, no I/O)."""

    if not 0 <= evidence_field_count <= total_evidence_fields or total_evidence_fields <= 0:
        raise ValueError("evidence counts must be valid proportions")

    asset_score = SEVERITY_SCORES.get(severity, 200)
    progress_score = min(sum(TACTIC_PROGRESS_WEIGHTS.get(t, 0) for t in mitre_tactics), 300)
    criticality_score = ASSET_CRITICALITY_SCORES.get(
        (asset_criticality or "").lower(), ASSET_CRITICALITY_SCORES["unknown"]
    )
    raw = asset_score + progress_score + criticality_score
    risk_score = min(max(raw, 0), MAX_SCORE)
    numeric_bucket = risk_score / MAX_SCORE
    if numeric_bucket >= 0.8:
        derived_severity = Severity.critical
    elif numeric_bucket >= 0.6:
        derived_severity = Severity.high
    elif numeric_bucket >= 0.35:
        derived_severity = Severity.medium
    elif numeric_bucket > 0.0:
        derived_severity = Severity.low
    else:
        derived_severity = Severity.informational

    confidence = round(evidence_field_count / total_evidence_fields, 4) if total_evidence_fields else 0.0
    confidence = min(max(confidence, 0.0), 1.0)

    return RiskAssessment(
        risk_score=risk_score,
        severity=derived_severity,
        confidence=confidence,
        asset_score=asset_score,
        progress_score=progress_score,
        criticality_score=criticality_score,
        tactic_coverage=sorted(set(mitre_tactics)),
        explanation=(
            f"score={risk_score} (asset={asset_score}, progress={progress_score}, "
            f"criticality={criticality_score})"
        ),
    )


def assess_alert(
    severity: Severity,
    mitre_payload: dict[str, Any],
    asset_attributes: dict[str, Any] | None = None,
    observed_fields: int = 0,
) -> RiskAssessment:
    """Convenience wrapper extracting tactics and criticality from alert data."""

    tactics: list[str] = []
    raw_tactics = mitre_payload.get("mitre_tactic") or mitre_payload.get("tactic") or []
    if isinstance(raw_tactics, str):
        tactics = [raw_tactics]
    elif isinstance(raw_tactics, list):
        tactics = [str(tactic) for tactic in raw_tactics]

    asset_criticality = None
    if isinstance(asset_attributes, dict):
        asset_criticality = asset_attributes.get("criticality")

    evidence_fields = observed_fields or 0
    return compute_risk_score(
        severity=severity,
        mitre_tactics=tactics,
        asset_criticality=asset_criticality,
        evidence_field_count=min(evidence_fields, 4),
        total_evidence_fields=4,
    )
