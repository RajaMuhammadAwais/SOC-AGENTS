from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    actor_user_id: UUID | None
    permissions: frozenset[str]


class DomainService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    def require_permission(self, permission: str) -> None:
        if permission not in self.context.permissions:
            raise PermissionError(f"Missing permission: {permission}")
