import json
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.v1.schemas import (
    LoginRequest,
    MessageResponse,
    MfaSetupResponse,
    MfaStatusResponse,
    MfaVerifyRequest,
    PrincipalResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.core.config import Settings, get_settings
from app.core.permissions import Principal, get_current_principal
from app.core.security import (
    create_access_token,
    generate_mfa_secret,
    generate_recovery_codes,
    generate_refresh_token,
    hash_password,
    hash_recovery_codes,
    hash_token,
    verify_password,
    verify_totp_code,
)
from app.domain.models import Permission, Role, RolePermission, Tenant, User, UserRole
from app.infrastructure.db.session import get_db_session
from app.infrastructure.redis.client import get_redis_client

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
RedisClient = Annotated[redis.Redis, Depends(get_redis_client)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
CurrentPrincipal = Annotated[Principal, Depends(get_current_principal)]

OWNER_PERMISSIONS = [
    "agents:run",
    "alerts:read",
    "alerts:update",
    "incidents:create",
    "incidents:read",
    "ingestion:write",
    "investigations:read",
    "investigations:update",
    "reports:read",
    "reports:write",
    "roles:read",
    "roles:write",
    "settings:read",
    "threat-intel:read",
    "users:read",
    "users:write",
]


async def store_refresh_token(
    *,
    redis_client: redis.Redis,
    refresh_token: str,
    settings: Settings,
    user_id: str,
    tenant_id: str,
    permissions: list[str],
) -> None:
    key = f"refresh-token:{hash_token(refresh_token)}"
    value = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "permissions": permissions,
        "created_at": datetime.now(UTC).isoformat(),
    }
    await redis_client.setex(
        key,
        settings.refresh_token_ttl_seconds,
        json.dumps(value),
    )


async def issue_tokens(
    *,
    redis_client: redis.Redis,
    settings: Settings,
    user_id: str,
    tenant_id: str,
    permissions: list[str],
) -> TokenResponse:
    access_token = create_access_token(
        subject=user_id,
        tenant_id=tenant_id,
        permissions=permissions,
        settings=settings,
    )
    refresh_token = generate_refresh_token()
    await store_refresh_token(
        redis_client=redis_client,
        refresh_token=refresh_token,
        settings=settings,
        user_id=user_id,
        tenant_id=tenant_id,
        permissions=permissions,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_ttl_seconds,
    )


async def load_user_permissions(session: AsyncSession, user_id: object) -> list[str]:
    permission_result = await session.execute(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return sorted(set(permission_result.scalars().all()))


def verify_user_mfa(user: User, code: str | None) -> bool:
    if not user.is_mfa_enabled:
        return True
    if not code:
        return False
    if user.mfa_secret and verify_totp_code(code, user.mfa_secret):
        return True

    code_hash = hash_token(code)
    recovery_codes = list(user.mfa_recovery_codes or [])
    if code_hash not in recovery_codes:
        return False

    recovery_codes.remove(code_hash)
    user.mfa_recovery_codes = recovery_codes
    return True


async def ensure_owner_permissions(session: AsyncSession) -> list[Permission]:
    result = await session.execute(select(Permission).where(Permission.name.in_(OWNER_PERMISSIONS)))
    existing = {permission.name: permission for permission in result.scalars().all()}
    missing = [
        Permission(name=name, description=f"Owner permission: {name}")
        for name in OWNER_PERMISSIONS
        if name not in existing
    ]
    session.add_all(missing)
    await session.flush()
    return [existing[name] for name in OWNER_PERMISSIONS if name in existing] + missing


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    session: DbSession,
    redis_client: RedisClient,
    settings: SettingsDependency,
) -> TokenResponse:
    tenant_exists = await session.execute(
        select(Tenant.id).where(Tenant.slug == payload.tenant_slug)
    )
    if tenant_exists.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug already exists",
        )

    tenant = Tenant(name=payload.tenant_name, slug=payload.tenant_slug)
    user = User(
        tenant=tenant,
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_mfa_enabled=False,
        mfa_recovery_codes=[],
    )
    role = Role(tenant_id=tenant.id, name="Owner", description="Tenant owner")
    session.add_all([tenant, user])
    await session.flush()
    role.tenant_id = tenant.id
    session.add(role)
    await session.flush()

    permissions = await ensure_owner_permissions(session)
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.add_all(
        [RolePermission(role_id=role.id, permission_id=permission.id) for permission in permissions]
    )
    await session.commit()

    return await issue_tokens(
        redis_client=redis_client,
        settings=settings,
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        permissions=OWNER_PERMISSIONS,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    session: DbSession,
    redis_client: RedisClient,
    settings: SettingsDependency,
) -> TokenResponse:
    user_result = await session.execute(
        select(User, Tenant)
        .join(Tenant, Tenant.id == User.tenant_id)
        .where(Tenant.slug == payload.tenant_slug)
        .where(Tenant.is_active.is_(True))
        .where(User.email == payload.email)
        .where(User.is_active.is_(True))
    )
    row = user_result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user, tenant = row
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not verify_user_mfa(user, payload.mfa_code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or MFA code",
        )
    await session.commit()

    permissions = await load_user_permissions(session, user.id)
    return await issue_tokens(
        redis_client=redis_client,
        settings=settings,
        user_id=str(user.id),
        tenant_id=str(tenant.id),
        permissions=permissions,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    redis_client: RedisClient,
    settings: SettingsDependency,
) -> TokenResponse:
    old_key = f"refresh-token:{hash_token(payload.refresh_token)}"
    stored = await redis_client.get(old_key)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    await redis_client.delete(old_key)
    token_data = json.loads(stored)
    permissions = [str(permission) for permission in token_data.get("permissions", [])]
    access_token = create_access_token(
        subject=str(token_data["user_id"]),
        tenant_id=str(token_data["tenant_id"]),
        permissions=permissions,
        settings=settings,
    )
    new_refresh_token = generate_refresh_token()
    await store_refresh_token(
        redis_client=redis_client,
        refresh_token=new_refresh_token,
        settings=settings,
        user_id=str(token_data["user_id"]),
        tenant_id=str(token_data["tenant_id"]),
        permissions=permissions,
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_ttl_seconds,
    )


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def setup_mfa(
    principal: CurrentPrincipal,
    session: DbSession,
) -> MfaSetupResponse:
    user = await session.get(User, UUID(principal.user_id))
    if user is None or str(user.tenant_id) != principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    secret = generate_mfa_secret()
    recovery_codes = generate_recovery_codes()
    user.mfa_secret = secret
    user.mfa_recovery_codes = hash_recovery_codes(recovery_codes)
    user.is_mfa_enabled = False
    await session.commit()
    return MfaSetupResponse(secret=secret, recovery_codes=recovery_codes)


@router.post("/mfa/enable", response_model=MfaStatusResponse)
async def enable_mfa(
    payload: MfaVerifyRequest,
    principal: CurrentPrincipal,
    session: DbSession,
) -> MfaStatusResponse:
    user = await session.get(User, UUID(principal.user_id))
    if user is None or str(user.tenant_id) != principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.mfa_secret or not verify_totp_code(payload.code, user.mfa_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    user.is_mfa_enabled = True
    await session.commit()
    return MfaStatusResponse(is_mfa_enabled=True)


@router.post("/mfa/disable", response_model=MfaStatusResponse)
async def disable_mfa(
    payload: MfaVerifyRequest,
    principal: CurrentPrincipal,
    session: DbSession,
) -> MfaStatusResponse:
    user = await session.get(User, UUID(principal.user_id))
    if user is None or str(user.tenant_id) != principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_user_mfa(user, payload.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")

    user.is_mfa_enabled = False
    user.mfa_secret = None
    user.mfa_recovery_codes = []
    await session.commit()
    return MfaStatusResponse(is_mfa_enabled=False)


@router.post("/logout", response_model=MessageResponse)
async def logout(principal: CurrentPrincipal) -> MessageResponse:
    return MessageResponse(message=f"Logout accepted for user {principal.user_id}")


@router.get("/me", response_model=PrincipalResponse)
async def current_user(principal: CurrentPrincipal) -> PrincipalResponse:
    return PrincipalResponse(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        permissions=sorted(principal.permissions),
    )
