# Investigation Agent

The Investigation Agent correlates incident events into an analyst-readable sequence. It is deterministic by design: every output comes from the supplied evidence, so the result can be reviewed, tested, and cited.

## Responsibilities

- Sort evidence into a chronological timeline.
- Identify affected hosts, accounts, and destination IPs.
- Infer likely initial access from common signals such as phishing, successful login, and CVE/exploit language.
- Flag suspected lateral movement from protocol and remote-access indicators such as RDP, WinRM, SMB, and remote login activity.
- Recommend the next investigation action based on observed scope and confidence.

## Implementation

Code lives in `backend/app/agents/investigation.py`.

The public entry point is `run_investigation(state)`. It performs four simple steps:

1. `build_timeline`
2. `identify_affected_assets`
3. `analyze_attack_chain`
4. `choose_investigation_next_action`

The agent intentionally avoids hidden model reasoning. It returns explicit fields such as `initial_access`, `lateral_movement`, `attack_chain`, `findings`, `confidence`, and `next_action`.

## Evidence Handling

Events are expected to contain fields such as:

- `event_id`
- `event_type`
- `occurred_at`
- `actor`
- `target`
- `source_ip`
- `destination_ip`
- `summary`

Missing fields are handled conservatively. Unknown initial access remains `unknown`, and lateral movement remains `not_observed` unless supporting evidence exists.

## Verification

Focused tests are in `backend/tests/test_investigation_agent.py` and cover timeline ordering, affected asset extraction, attack-chain analysis, next-action selection, and end-to-end investigation output.
