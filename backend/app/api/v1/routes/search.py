from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import CursorPage, NormalizedEventSummary
from app.core.permissions import Principal, require_permission
from app.domain.models import NormalizedEvent
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/events", response_model=CursorPage[NormalizedEventSummary])
async def search_events(
    event_type: str | None = None,
    source_ip: str | None = None,
    actor: str | None = None,
    occurred_after: datetime | None = None,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("alerts:read")),
    limit: int = Query(default=100, ge=1, le=500),
) -> CursorPage[NormalizedEventSummary]:
    query = select(NormalizedEvent).where(
        NormalizedEvent.tenant_id == UUID(principal.tenant_id)
    )
    if event_type:
        query = query.where(NormalizedEvent.event_type == event_type)
    if source_ip:
        query = query.where(NormalizedEvent.source_ip == source_ip)
    if actor:
        query = query.where(NormalizedEvent.actor == actor)
    if occurred_after:
        query = query.where(NormalizedEvent.occurred_at >= occurred_after)

    result = await session.execute(query.order_by(NormalizedEvent.occurred_at.desc()).limit(limit))
    return CursorPage[NormalizedEventSummary](
        items=[
            NormalizedEventSummary(
                id=event.id,
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                actor=event.actor,
                target=event.target,
                source_ip=event.source_ip,
                destination_ip=event.destination_ip,
            )
            for event in result.scalars().all()
        ]
    )
