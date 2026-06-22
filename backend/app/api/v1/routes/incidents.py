from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import CursorPage, IncidentCreate, IncidentSummary
from app.core.permissions import Principal, require_permission
from app.domain.models import Incident, IncidentAlert, IncidentStatus, Severity
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=CursorPage[IncidentSummary])
async def list_incidents(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("incidents:read")),
) -> CursorPage[IncidentSummary]:
    result = await session.execute(
        select(Incident)
        .where(Incident.tenant_id == UUID(principal.tenant_id))
        .order_by(Incident.updated_at.desc())
        .limit(100)
    )
    return CursorPage[IncidentSummary](
        items=[
            IncidentSummary(
                id=incident.id,
                title=incident.title,
                severity=incident.severity.value,
                status=incident.status.value,
                updated_at=incident.updated_at,
            )
            for incident in result.scalars().all()
        ],
    )


@router.post("", response_model=IncidentSummary, status_code=201)
async def create_incident(
    payload: IncidentCreate,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("incidents:create")),
) -> IncidentSummary:
    incident = Incident(
        tenant_id=UUID(principal.tenant_id),
        title=payload.title,
        summary=payload.summary,
        severity=Severity(payload.severity),
        status=IncidentStatus.open,
        owner_user_id=UUID(principal.user_id),
    )
    session.add(incident)
    await session.flush()
    for alert_id in payload.alert_ids:
        session.add(IncidentAlert(incident_id=incident.id, alert_id=alert_id))
    await session.commit()
    await session.refresh(incident)
    return IncidentSummary(
        id=incident.id,
        title=incident.title,
        severity=incident.severity.value,
        status=incident.status.value,
        updated_at=incident.updated_at,
    )
