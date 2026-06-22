# Agent State Persistence

Agent state persistence records agent runs and step-level state transitions using the existing SQLAlchemy models.

## Existing Tables

- `agent_runs`: run metadata, status, model, graph thread ID, token usage, and trace payload.
- `agent_steps`: node-level input/output state and tool-call metadata.

## Implementation

Code lives in `backend/app/agents/state.py`.

`AgentStateStore` provides:

- `create_run`
- `mark_running`
- `record_step`
- `complete_run`
- `fail_run`

The store is tenant-scoped and rejects cross-tenant run access. It flushes changes but does not commit, so API routes and workers can control transaction boundaries.

## State Contract

Initial state is stored in `AgentRun.trace.initial_state`.
Final state is stored in `AgentRun.trace.final_state`.
Each graph node or agent step can be stored as an `AgentStep` with input state, output state, and optional tool-call metadata.

## Verification

Focused tests are in `backend/tests/test_agent_state_store.py` and cover run creation, step recording, completion, token usage, and cross-tenant rejection.
