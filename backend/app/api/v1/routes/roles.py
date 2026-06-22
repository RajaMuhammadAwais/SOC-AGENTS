from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.v1.schemas import (
    AssignRoleRequest,
    CursorPage,
    MessageResponse,
    RoleCreate,
    RoleSummary,
)
from app.core.permissions import Principal, require_permission
from app.domain.models import Permission, Role, RolePermission, User, UserRole
from app.infrastructure.db.session import get_db_session

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=CursorPage[RoleSummary])
async def list_roles(
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("roles:read")),
) -> CursorPage[RoleSummary]:
    result = await session.execute(
        select(Role).where(Role.tenant_id == UUID(principal.tenant_id)).order_by(Role.created_at.desc())
    )
    return CursorPage[RoleSummary](
        items=[
            RoleSummary(id=role.id, name=role.name, description=role.description)
            for role in result.scalars().all()
        ]
    )


@router.post("", response_model=RoleSummary, status_code=201)
async def create_role(
    payload: RoleCreate,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("roles:write")),
) -> RoleSummary:
    role = Role(
        tenant_id=UUID(principal.tenant_id),
        name=payload.name,
        description=payload.description,
    )
    session.add(role)
    await session.flush()
    for permission_name in payload.permissions:
        permission_result = await session.execute(
            select(Permission).where(Permission.name == permission_name)
        )
        permission = permission_result.scalar_one_or_none()
        if permission is None:
            permission = Permission(name=permission_name, description=None)
            session.add(permission)
            await session.flush()
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    await session.commit()
    await session.refresh(role)
    return RoleSummary(id=role.id, name=role.name, description=role.description)


@router.post("/assignments", response_model=MessageResponse, status_code=201)
async def assign_role(
    payload: AssignRoleRequest,
    session: AsyncSession = Depends(get_db_session),
    principal: Principal = Depends(require_permission("roles:write")),
) -> MessageResponse:
    tenant_id = UUID(principal.tenant_id)
    user_result = await session.execute(
        select(User).where(User.id == payload.user_id, User.tenant_id == tenant_id)
    )
    role_result = await session.execute(
        select(Role).where(Role.id == payload.role_id, Role.tenant_id == tenant_id)
    )
    if user_result.scalar_one_or_none() is None or role_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User or role not found",
        )

    session.add(UserRole(user_id=payload.user_id, role_id=payload.role_id))
    await session.commit()
    return MessageResponse(message="Role assigned")
