# Response Agent

The Response Agent recommends and prepares containment, evidence, and notification actions. It is approval-gated by default and does not directly call firewall, identity, EDR, or ticketing systems.

## Source Basis

- NIST SP 800-61 Rev. 3, verified on 2026-06-11: incident-response practices should reduce incident impact and improve detection, response, and recovery activities.

## Supported Actions

- `block_ip`
- `disable_account`
- `isolate_host`
- `reset_password`
- `collect_forensics`
- `notify_owner`

## Safety Model

Actions that can disrupt users, hosts, or network access require approval. If approval is missing, the agent returns `blocked_actions` and `next_action=request_human_approval`.

Even with approval, actions are only marked as executed when `execution_mode=execute`. The current implementation records intended execution in state; integrations with EDR, IAM, firewall, SOAR, or ticketing systems should be added as separate infrastructure adapters.

## Implementation

Code lives in `backend/app/agents/response.py`.

The public entry point is `run_response(state)`. It performs:

1. `recommend_response_actions`
2. `execute_response_actions`

## Verification

Focused tests are in `backend/tests/test_response_agent.py` and cover recommendation generation, approval blocking, recommendation-only mode, and approved execution mode.
