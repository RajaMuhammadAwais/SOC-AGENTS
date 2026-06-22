from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import MessageResponse, RawEventIngestRequest
from app.core.permissions import Principal, require_permission
from app.domain.models import RawEvent
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/events", response_model=MessageResponse)
async def ingest_events(
    payload: RawEventIngestRequest,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("ingestion:write")),
) -> MessageResponse:
    event = RawEvent(
        tenant_id=UUID(principal.tenant_id),
        data_source_id=payload.data_source_id,
        source_event_id=payload.source_event_id,
        occurred_at=payload.occurred_at,
        received_at=datetime.now(UTC),
        payload=payload.payload,
    )
    session.add(event)
    await session.commit()
    return MessageResponse(message=f"Event {event.id} ingested")
