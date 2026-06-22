from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.triage import choose_next_action, generate_ai_triage_findings
from app.api.v1.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentRunSummary,
    AgentTriagePreviewResponse,
    CursorPage,
)
from app.core.config import Settings, get_settings
from app.core.permissions import Principal, require_permission
from app.domain.llm import LLMClient, LLMConfigurationError, LLMProviderError
from app.domain.models import AgentRun
from app.infrastructure.db.session import get_db_session
from app.infrastructure.llm import OpenRouterClient

router = APIRouter(prefix="/agents", tags=["agents"])
AgentsRunPrincipal = Annotated[Principal, Depends(require_permission("agents:run"))]
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_agent_llm_client(settings: SettingsDependency) -> LLMClient:
    if settings.llm_provider != "openrouter":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unsupported LLM provider: {settings.llm_provider}",
        )
    try:
        return OpenRouterClient.from_settings(settings)
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


LLMClientDependency = Annotated[LLMClient, Depends(get_agent_llm_client)]


@router.get("/runs", response_model=CursorPage[AgentRunSummary])
async def list_agent_runs(
    session: DbSession,
    principal: AgentsRunPrincipal,
) -> CursorPage[AgentRunSummary]:
    result = await session.execute(
        select(AgentRun)
        .where(AgentRun.tenant_id == UUID(principal.tenant_id))
        .order_by(AgentRun.created_at.desc())
        .limit(100)
    )
    return CursorPage[AgentRunSummary](
        items=[
            AgentRunSummary(
                id=run.id,
                agent_name=run.agent_name,
                status=run.status.value,
                created_at=run.created_at,
            )
            for run in result.scalars().all()
        ]
    )


@router.post("/triage-runs", response_model=AgentRunResponse, status_code=202)
async def start_triage_run(
    payload: AgentRunRequest,
    principal: AgentsRunPrincipal,
) -> AgentRunResponse:
    return AgentRunResponse(run_id=uuid4(), status="queued")


@router.post("/triage-preview", response_model=AgentTriagePreviewResponse)
async def preview_triage_run(
    payload: AgentRunRequest,
    principal: AgentsRunPrincipal,
    llm_client: LLMClientDependency,
) -> AgentTriagePreviewResponse:
    try:
        findings = await generate_ai_triage_findings(
            {
                "tenant_id": principal.tenant_id,
                "alert_id": str(payload.alert_id) if payload.alert_id else "",
                "objective": payload.objective,
            },
            llm_client,
        )
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    next_action = choose_next_action(findings)
    return AgentTriagePreviewResponse(
        severity=findings["severity"],
        category=findings["category"],
        confidence=findings["confidence"],
        rationale=findings["rationale"],
        next_action=next_action["next_action"],
    )
