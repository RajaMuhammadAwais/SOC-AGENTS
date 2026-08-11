#!/usr/bin/env python3
"""Seeds the demo tenant, roles, permissions and an analyst user.

Idempotent: re-running updates the demo user's password and reconciles the
role/permission assignments without duplicating rows.

Usage:
    env APP_ENV=local DATABASE_URL=postgresql+asyncpg://soc:soc@localhost:5432/soc \
        python scripts/seed_demo_tenant.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import generate_mfa_secret, hash_password
from app.domain.models import (
    Permission,
    Role,
    RolePermission,
    Tenant,
    User,
    UserRole,
)
from app.infrastructure.db.session import AsyncSessionFactory

TENANT_NAME = "Acme Corporation"
TENANT_SLUG = "acme"
ADMIN_EMAIL = "analyst@acme.local"
ADMIN_PASSWORD = os.environ.get("DEMO_PASSWORD", "StrongPass1234!")
ADMIN_FULL_NAME = "Alex Analyst"

PERMISSIONS: list[tuple[str, str]] = [
    ("alerts.read", "Read alerts"),
    ("alerts.write", "Update alert status and triage decisions"),
    ("alerts.assign", "Assign alerts and incidents"),
    ("incidents.read", "Read incidents"),
    ("incidents.write", "Manage incidents and playbooks"),
    ("investigations.read", "Read investigations"),
    ("investigations.write", "Create and manage investigations"),
    ("data_sources.read", "List data sources"),
    ("data_sources.write", "Manage data sources and upload events"),
    ("agents.read", "Read agent runs and autonomy settings"),
    ("agents.write", "Manage agent skills, knowledge and autonomy policy"),
    ("users.read", "Read users"),
    ("users.write", "Manage users and roles"),
    ("settings.read", "Read tenant settings"),
    ("settings.write", "Update tenant settings"),
    ("reports.read", "Read reports"),
    ("reports.write", "Generate reports"),
]

ROLES: dict[str, tuple[str, list[str]]] = {
    "soc_admin": ("SOC Administrator — full platform access", [perm for perm, _ in PERMISSIONS]),
    "manager": ("SOC Manager — triage, incidents and team oversight", [
        "alerts.read", "alerts.write", "alerts.assign",
        "incidents.read", "incidents.write",
        "investigations.read", "investigations.write",
        "agents.read", "users.read", "reports.read", "reports.write",
        "settings.read",
    ]),
    "analyst": ("SOC Analyst — triage and investigation", [
        "alerts.read", "alerts.write", "alerts.assign",
        "incidents.read", "incidents.write",
        "investigations.read", "investigations.write",
        "data_sources.read", "data_sources.write",
        "agents.read", "reports.read",
    ]),
}


async def seed() -> None:
    async with AsyncSessionFactory() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name=TENANT_NAME, slug=TENANT_SLUG)
            session.add(tenant)
            await session.flush()

        created_permissions: dict[str, Permission] = {}
        for name, description in PERMISSIONS:
            perm = (
                await session.execute(select(Permission).where(Permission.name == name))
            ).scalar_one_or_none()
            if perm is None:
                perm = Permission(name=name, description=description)
                session.add(perm)
                await session.flush()
            created_permissions[name] = perm

        for role_name, (description, perm_names) in ROLES.items():
            role = (
                await session.execute(
                    select(Role).where(Role.tenant_id == tenant.id, Role.name == role_name)
                )
            ).scalar_one_or_none()
            if role is None:
                role = Role(tenant_id=tenant.id, name=role_name, description=description)
                session.add(role)
                await session.flush()
            for perm_name in perm_names:
                existing_rp = (
                    await session.execute(
                        select(RolePermission).where(
                            RolePermission.role_id == role.id,
                            RolePermission.permission_id == created_permissions[perm_name].id,
                        )
                    )
                ).scalar_one_or_none()
                if existing_rp is None:
                    session.add(
                        RolePermission(
                            role_id=role.id,
                            permission_id=created_permissions[perm_name].id,
                        )
                    )
            await session.flush()

        user = (
            await session.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == ADMIN_EMAIL)
            )
        ).scalar_one_or_none()
        if user is None:
            user = User(
                tenant_id=tenant.id,
                email=ADMIN_EMAIL,
                full_name=ADMIN_FULL_NAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                is_mfa_enabled=False,
                mfa_secret=generate_mfa_secret(),
                mfa_recovery_codes=[],
            )
            session.add(user)
            await session.flush()
        else:
            user.password_hash = hash_password(ADMIN_PASSWORD)
            await session.flush()

        analyst_role = (
            await session.execute(
                select(Role).where(Role.tenant_id == tenant.id, Role.name == "analyst")
            )
        ).scalar_one()
        if not (
            await session.execute(
                select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == analyst_role.id)
            )
        ).scalar_one_or_none():
            session.add(UserRole(user_id=user.id, role_id=analyst_role.id))

        await session.commit()

        print(f"tenant: {tenant.id} ({tenant.slug})", file=sys.stderr)
        print(f"user: {user.id} ({user.email})", file=sys.stderr)
        print(
            f"roles: {', '.join(ROLES.keys())}, permissions: {len(PERMISSIONS)}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    asyncio.run(seed())
