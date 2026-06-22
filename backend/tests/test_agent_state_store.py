from uuid import uuid4

import pytest

from app.agents.state import AgentStateStore
from app.domain.agents import AgentName
from app.domain.models import AgentRun, AgentRunStatus


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.runs: dict[object, AgentRun] = {}
        self.flush_count = 0

    def add(self, value: object) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flush_count += 1

    async def get(self, model: type[AgentRun], resource_id: object) -> AgentRun | None:
        assert model is AgentRun
        return self.runs.get(resource_id)


@pytest.mark.asyncio
async def test_create_run_persists_initial_state() -> None:
    tenant_id = uuid4()
    session = FakeSession()
    store = AgentStateStore(session, tenant_id)  # type: ignore[arg-type]

    run = await store.create_run(AgentName.alert_triage, {"objective": "triage alert"})

    assert run.tenant_id == tenant_id
    assert run.agent_name == "alert_triage"
    assert run.status == AgentRunStatus.queued
    assert run.trace == {"initial_state": {"objective": "triage alert"}}
    assert session.added == [run]
    assert session.flush_count == 1


@pytest.mark.asyncio
async def test_record_step_requires_tenant_owned_run() -> None:
    tenant_id = uuid4()
    run_id = uuid4()
    session = FakeSession()
    session.runs[run_id] = AgentRun(
        id=run_id,
        tenant_id=tenant_id,
        agent_name="alert_triage",
        status=AgentRunStatus.running,
        token_usage={},
        trace={},
    )
    store = AgentStateStore(session, tenant_id)  # type: ignore[arg-type]

    step = await store.record_step(
        run_id,
        "classify",
        {"severity": "high"},
        {"category": "identity"},
    )

    assert step.tenant_id == tenant_id
    assert step.agent_run_id == run_id
    assert step.node_name == "classify"
    assert step.output_state == {"category": "identity"}


@pytest.mark.asyncio
async def test_complete_run_updates_status_trace_and_token_usage() -> None:
    tenant_id = uuid4()
    run_id = uuid4()
    run = AgentRun(
        id=run_id,
        tenant_id=tenant_id,
        agent_name="risk_scoring",
        status=AgentRunStatus.running,
        token_usage={},
        trace={"initial_state": {}},
    )
    session = FakeSession()
    session.runs[run_id] = run
    store = AgentStateStore(session, tenant_id)  # type: ignore[arg-type]

    result = await store.complete_run(run_id, {"risk_score": 91}, token_usage={"total": 12})

    assert result.status == AgentRunStatus.completed
    assert result.trace["final_state"] == {"risk_score": 91}
    assert result.token_usage == {"total": 12}


@pytest.mark.asyncio
async def test_fail_run_rejects_cross_tenant_access() -> None:
    tenant_id = uuid4()
    run_id = uuid4()
    session = FakeSession()
    session.runs[run_id] = AgentRun(
        id=run_id,
        tenant_id=uuid4(),
        agent_name="response",
        status=AgentRunStatus.running,
        token_usage={},
        trace={},
    )
    store = AgentStateStore(session, tenant_id)  # type: ignore[arg-type]

    with pytest.raises(LookupError, match="Agent run not found for tenant"):
        await store.fail_run(run_id, "boom")
