import pytest
from fastapi import HTTPException

from app.core.permissions import Principal, require_permission


@pytest.mark.asyncio
async def test_require_permission_allows_matching_permission() -> None:
    principal = Principal(
        user_id="user-1",
        tenant_id="tenant-1",
        permissions=frozenset({"alerts:read"}),
    )

    dependency = require_permission("alerts:read")

    assert await dependency(principal) == principal


@pytest.mark.asyncio
async def test_require_permission_rejects_missing_permission() -> None:
    principal = Principal(
        user_id="user-1",
        tenant_id="tenant-1",
        permissions=frozenset(),
    )

    dependency = require_permission("alerts:read")

    with pytest.raises(HTTPException) as exc_info:
        await dependency(principal)

    assert exc_info.value.status_code == 403
