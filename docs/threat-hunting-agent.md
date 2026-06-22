# Threat Hunting Agent

The Threat Hunting Agent searches supplied security events for activity similar to a hunt hypothesis or seed indicators. It is evidence-driven and deterministic so hunters can review why events matched.

## Source Basis

- MITRE ATT&CK Data & Tools, verified on 2026-06-11: ATT&CK recommends STIX and related tooling for automated workflows and keeping up with the evolving knowledge base.
- MITRE ATT&CK Data Sources, verified on 2026-06-11: legacy data sources describe telemetry categories such as logon session, network traffic, process, script, and user account. MITRE marks this page deprecated as of ATT&CK v18, so this implementation keeps the terms as compatibility labels rather than treating them as the future data model.
- NIST SP 800-53 Rev. 5, verified on 2026-06-11: system monitoring and incident response controls remain a baseline reference for defensive monitoring programs.

## Responsibilities

- Build a simple hunt query from a hypothesis and seed indicators.
- Infer likely telemetry needs for the hunt.
- Match supplied events against query terms.
- Extract similar actors, targets, source IPs, and destination IPs.
- Report telemetry coverage gaps before escalating findings.
- Recommend the next hunt action.

## Implementation

Code lives in `backend/app/agents/threat_hunting.py`.

The public entry point is `run_threat_hunt(state)`. It performs four steps:

1. `build_hunt_query`
2. `find_similar_events`
3. `summarize_hunt_results`
4. `choose_hunt_next_action`

The agent does not call external services or generate hidden reasoning. Future work can replace the in-memory event matcher with database, SIEM, or vector search adapters while keeping the same state contract.

## Verification

Focused tests are in `backend/tests/test_threat_hunting_agent.py` and cover query planning, event matching, entity extraction, coverage-gap handling, and end-to-end hunt execution.
