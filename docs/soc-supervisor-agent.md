# SOC Supervisor Agent

The SOC Supervisor Agent is the high-level routing layer for specialist SOC agents. It behaves like an analyst dispatcher: inspect the objective and available context, select the best specialist, assign priority, and return a clear rationale.

## Responsibilities

- Route containment and isolation work to the Response Agent first.
- Route incident, timeline, and root-cause work to the Investigation Agent.
- Route observables, CVEs, hashes, and reputation checks to the Threat Intelligence Agent.
- Route hunt and similarity requests to the Threat Hunting Agent.
- Route risk and impact requests to the Risk Scoring Agent.
- Route reports, executive summaries, and RCA requests to the Report Generation Agent.
- Default new security alerts to the Alert Triage Agent.

## Implementation

Code lives in `backend/app/agents/supervisor.py`.

The public entry point is `route_soc_work(state)`. It returns:

- `selected_agent`
- `priority`
- `rationale`
- `next_action`

The implementation uses auditable routing rules rather than opaque model output. This keeps orchestration predictable, testable, and suitable for security operations workflows where decisions need to be explained.

## Priority Rules

- Response work becomes `critical` when severity is critical, otherwise `high`.
- Critical and high incident work becomes `high`.
- Medium or unknown work stays `medium`.
- Low and informational work becomes `low`.

## Verification

Focused tests are in `backend/tests/test_supervisor_agent.py` and cover response precedence, incident routing, observable routing, and the default alert-triage path.
