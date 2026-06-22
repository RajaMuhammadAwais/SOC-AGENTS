from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import CursorPage, ReportCreate, ReportSummary
from app.core.permissions import Principal, require_permission
from app.domain.models import Report
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=CursorPage[ReportSummary])
async def list_reports(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("reports:read")),
) -> CursorPage[ReportSummary]:
    result = await session.execute(
        select(Report)
        .where(Report.tenant_id == UUID(principal.tenant_id))
        .order_by(Report.updated_at.desc())
        .limit(100)
    )
    return CursorPage[ReportSummary](
        items=[
            ReportSummary(
                id=report.id,
                incident_id=report.incident_id,
                report_type=report.report_type,
                status=report.status,
                updated_at=report.updated_at,
            )
            for report in result.scalars().all()
        ]
    )


@router.post("", response_model=ReportSummary, status_code=201)
async def create_report(
    payload: ReportCreate,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("reports:write")),
) -> ReportSummary:
    report = Report(
        tenant_id=UUID(principal.tenant_id),
        incident_id=payload.incident_id,
        report_type=payload.report_type,
        status="draft",
        content={},
        citations={},
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return ReportSummary(
        id=report.id,
        incident_id=report.incident_id,
        report_type=report.report_type,
        status=report.status,
        updated_at=report.updated_at,
    )
