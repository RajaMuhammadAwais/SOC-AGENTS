# Report Generation Agent

The Report Generation Agent creates structured incident reports for different audiences. It avoids unconstrained prose generation and returns predictable sections that can be rendered by APIs, PDFs, dashboards, or case-management workflows.

## Source Basis

- NIST SP 800-61 Rev. 3, verified on 2026-06-11: incident-response recommendations should help organizations prepare, reduce incident impact, and improve detection, response, and recovery.

## Report Types

- `executive`: risk, business impact, and decisions needed.
- `technical`: timeline, affected assets, findings, and recommended actions.
- `rca` / `root_cause`: root cause, contributing factors, and corrective actions.

## Implementation

Code lives in `backend/app/agents/report_generation.py`.

The public entry point is `run_report_generation(state)`. It routes to:

1. `build_executive_report`
2. `build_technical_report`
3. `build_rca_report`

Each report includes a common base with incident ID, title, summary, risk level, risk score, and citations.

## Verification

Focused tests are in `backend/tests/test_report_generation_agent.py` and cover executive, technical, RCA, and report-type routing behavior.
