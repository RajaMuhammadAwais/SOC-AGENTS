from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import CursorPage, InvestigationCreate, InvestigationSummary
from app.core.permissions import Principal, require_permission
from app.domain.models import Investigation
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.get("", response_model=CursorPage[InvestigationSummary])
async def list_investigations(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("investigations:read")),
) -> CursorPage[InvestigationSummary]:
    result = await session.execute(
        select(Investigation)
        .where(Investigation.tenant_id == UUID(principal.tenant_id))
        .order_by(Investigation.updated_at.desc())
        .limit(100)
    )
    return CursorPage[InvestigationSummary](
        items=[
            InvestigationSummary(
                id=investigation.id,
                incident_id=investigation.incident_id,
                title=investigation.title,
                status=investigation.status,
                updated_at=investigation.updated_at,
            )
            for investigation in result.scalars().all()
        ]
    )


@router.post("", response_model=InvestigationSummary, status_code=201)
async def create_investigation(
    payload: InvestigationCreate,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("investigations:update")),
) -> InvestigationSummary:
    investigation = Investigation(
        tenant_id=UUID(principal.tenant_id),
        incident_id=payload.incident_id,
        title=payload.title,
        status="open",
        findings={},
    )
    session.add(investigation)
    await session.commit()
    await session.refresh(investigation)
    return InvestigationSummary(
        id=investigation.id,
        incident_id=investigation.incident_id,
        title=investigation.title,
        status=investigation.status,
        updated_at=investigation.updated_at,
    )
