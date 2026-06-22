from fastapi import APIRouter, Depends

from app.api.v1.schemas import MessageResponse
from app.core.permissions import Principal, require_permission

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=MessageResponse)
async def get_settings_summary(
    principal: Principal = Depends(require_permission("settings:read")),
) -> MessageResponse:
    return MessageResponse(message=f"Settings placeholder for tenant {principal.tenant_id}")
