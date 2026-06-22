import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import CursorPage, ObservableCreate, ObservableSummary
from app.core.permissions import Principal, require_permission
from app.domain.models import Observable
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/threat-intel", tags=["threat-intel"])


@router.get("/observables", response_model=CursorPage[ObservableSummary])
async def list_observables(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("threat-intel:read")),
) -> CursorPage[ObservableSummary]:
    result = await session.execute(
        select(Observable)
        .where(Observable.tenant_id == UUID(principal.tenant_id))
        .order_by(Observable.created_at.desc())
        .limit(100)
    )
    return CursorPage[ObservableSummary](
        items=[
            ObservableSummary(
                id=observable.id,
                type=observable.type,
                value=observable.value,
                created_at=observable.created_at,
            )
            for observable in result.scalars().all()
        ]
    )


@router.post("/observables", response_model=ObservableSummary, status_code=201)
async def create_observable(
    payload: ObservableCreate,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("threat-intel:read")),
) -> ObservableSummary:
    observable = Observable(
        tenant_id=UUID(principal.tenant_id),
        type=payload.type,
        value=payload.value,
        value_hash=hashlib.sha256(payload.value.encode("utf-8")).hexdigest(),
    )
    session.add(observable)
    await session.commit()
    await session.refresh(observable)
    return ObservableSummary(
        id=observable.id,
        type=observable.type,
        value=observable.value,
        created_at=observable.created_at,
    )
