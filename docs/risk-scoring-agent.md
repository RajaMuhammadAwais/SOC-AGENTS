# Risk Scoring Agent

The Risk Scoring Agent produces an explainable 0-100 SOC risk score. It treats risk as a combination of likelihood and impact, then returns the score, risk band, contributing reasons, and a recommended next action.

## Source Basis

- NIST SP 800-30 Rev. 1, verified on 2026-06-11: risk assessment supports risk-management decisions and senior-leader courses of action.
- FIRST CVSS v4.0 Specification, verified on 2026-06-11: CVSS provides standardized vulnerability severity, but consumers should refine severity with threat and environmental context for more meaningful risk input.

## Responsibilities

- Calculate a likelihood score from alert severity, exploitation signals, exposure, duplicates, and detection confidence.
- Calculate an impact score from asset criticality, data sensitivity, affected asset count, and CVSS severity.
- Combine likelihood and impact into a 0-100 risk score.
- Map the score to `informational`, `low`, `medium`, `high`, or `critical`.
- Return explanation lines for auditability.

## Implementation

Code lives in `backend/app/agents/risk_scoring.py`.

The public entry point is `run_risk_scoring(state)`. It performs three steps:

1. `calculate_likelihood_score`
2. `calculate_impact_score`
3. `calculate_risk_score`

The formula is intentionally simple and deterministic. CVSS is used as one technical-impact input, not as the full SOC risk score.

## Verification

Focused tests are in `backend/tests/test_risk_scoring_agent.py` and cover likelihood scoring, low-confidence adjustment, impact scoring, level boundaries, and end-to-end risk scoring.
