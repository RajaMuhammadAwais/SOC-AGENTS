from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.v1.schemas import AlertCreate, AlertSummary, AlertUpdate, CursorPage
from app.core.permissions import Principal, require_permission
from app.domain.models import Alert, AlertStatus, Severity
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=CursorPage[AlertSummary])
async def list_alerts(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("alerts:read")),
) -> CursorPage[AlertSummary]:
    result = await session.execute(
        select(Alert)
        .where(Alert.tenant_id == UUID(principal.tenant_id))
        .order_by(Alert.created_at.desc())
        .limit(100)
    )
    return CursorPage[AlertSummary](
        items=[
            AlertSummary(
                id=alert.id,
                title=alert.title,
                severity=alert.severity.value,
                status=alert.status.value,
                source=alert.source,
                created_at=alert.created_at,
            )
            for alert in result.scalars().all()
        ],
    )


@router.post("", response_model=AlertSummary, status_code=201)
async def create_alert(
    payload: AlertCreate,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("alerts:update")),
) -> AlertSummary:
    alert = Alert(
        tenant_id=UUID(principal.tenant_id),
        title=payload.title,
        description=payload.description,
        severity=Severity(payload.severity),
        status=AlertStatus.new,
        source=payload.source,
        risk_score=payload.risk_score,
        mitre=payload.mitre,
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return AlertSummary(
        id=alert.id,
        title=alert.title,
        severity=alert.severity.value,
        status=alert.status.value,
        source=alert.source,
        created_at=alert.created_at,
    )


@router.patch("/{alert_id}", response_model=AlertSummary)
async def update_alert(
    alert_id: UUID,
    payload: AlertUpdate,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("alerts:update")),
) -> AlertSummary:
    result = await session.execute(
        select(Alert).where(Alert.tenant_id == UUID(principal.tenant_id), Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if payload.status is not None:
        alert.status = AlertStatus(payload.status)
    if payload.severity is not None:
        alert.severity = Severity(payload.severity)
    if payload.risk_score is not None:
        alert.risk_score = payload.risk_score
    await session.commit()
    await session.refresh(alert)
    return AlertSummary(
        id=alert.id,
        title=alert.title,
        severity=alert.severity.value,
        status=alert.status.value,
        source=alert.source,
        created_at=alert.created_at,
    )
