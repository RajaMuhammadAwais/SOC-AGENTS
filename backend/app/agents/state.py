from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agents import AgentName
from app.domain.models import AgentRun, AgentRunStatus, AgentStep


class AgentStateStore:
    def __init__(self, session: AsyncSession, tenant_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def create_run(
        self,
        agent_name: AgentName | str,
        initial_state: dict[str, object],
        *,
        alert_id: UUID | None = None,
        incident_id: UUID | None = None,
        investigation_id: UUID | None = None,
        model: str | None = None,
        graph_thread_id: str | None = None,
    ) -> AgentRun:
        run = AgentRun(
            tenant_id=self.tenant_id,
            alert_id=alert_id,
            incident_id=incident_id,
            investigation_id=investigation_id,
            agent_name=_agent_name_value(agent_name),
            status=AgentRunStatus.queued,
            model=model,
            graph_thread_id=graph_thread_id,
            token_usage={},
            trace={"initial_state": initial_state},
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def mark_running(self, agent_run_id: UUID) -> AgentRun:
        run = await self._get_owned_run(agent_run_id)
        run.status = AgentRunStatus.running
        await self.session.flush()
        return run

    async def record_step(
        self,
        agent_run_id: UUID,
        node_name: str,
        input_state: dict[str, object],
        output_state: dict[str, object],
        *,
        tool_calls: dict[str, object] | None = None,
    ) -> AgentStep:
        await self._get_owned_run(agent_run_id)
        step = AgentStep(
            tenant_id=self.tenant_id,
            agent_run_id=agent_run_id,
            node_name=node_name,
            input_state=input_state,
            output_state=output_state,
            tool_calls=tool_calls or {},
        )
        self.session.add(step)
        await self.session.flush()
        return step

    async def complete_run(
        self,
        agent_run_id: UUID,
        final_state: dict[str, object],
        *,
        token_usage: dict[str, object] | None = None,
    ) -> AgentRun:
        run = await self._get_owned_run(agent_run_id)
        run.status = AgentRunStatus.completed
        run.trace = {**(run.trace or {}), "final_state": final_state}
        if token_usage is not None:
            run.token_usage = token_usage
        await self.session.flush()
        return run

    async def fail_run(self, agent_run_id: UUID, error: str) -> AgentRun:
        run = await self._get_owned_run(agent_run_id)
        run.status = AgentRunStatus.failed
        run.trace = {**(run.trace or {}), "error": error}
        await self.session.flush()
        return run

    async def _get_owned_run(self, agent_run_id: UUID) -> AgentRun:
        run = await self.session.get(AgentRun, agent_run_id)
        if run is None or run.tenant_id != self.tenant_id:
            raise LookupError("Agent run not found for tenant")
        return run


def _agent_name_value(agent_name: AgentName | str) -> str:
    if isinstance(agent_name, AgentName):
        return agent_name.value
    return agent_name
