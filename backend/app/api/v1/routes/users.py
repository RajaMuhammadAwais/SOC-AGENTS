from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas import CursorPage, UserCreate, UserSummary
from app.core.permissions import Principal, require_permission
from app.core.security import hash_password
from app.domain.models import User
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=CursorPage[UserSummary])
async def list_users(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("users:read")),
) -> CursorPage[UserSummary]:
    result = await session.execute(
        select(User)
        .where(User.tenant_id == UUID(principal.tenant_id))
        .order_by(User.created_at.desc())
    )
    return CursorPage[UserSummary](
        items=[
            UserSummary(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
            )
            for user in result.scalars().all()
        ]
    )


@router.post("", response_model=UserSummary, status_code=201)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("users:write")),
) -> UserSummary:
    user = User(
        tenant_id=UUID(principal.tenant_id),
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_mfa_enabled=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserSummary(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
    )
