from datetime import UTC, datetime

import redis.asyncio as redis
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException

from app.infrastructure.db.session import get_db_session
from app.infrastructure.redis.client import get_redis_client


class HealthResponse(BaseModel):
    status: str
    service: str
    checked_at: datetime


router = APIRouter()


@router.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="api",
        checked_at=datetime.now(UTC),
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(
    session: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
) -> HealthResponse:
    try:
        await session.execute(text("select 1"))
        await redis_client.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="One or more dependencies are unavailable",
        ) from exc

    return HealthResponse(
        status="ok",
        service="api",
        checked_at=datetime.now(UTC),
    )
