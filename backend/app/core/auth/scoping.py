import uuid
from dataclasses import dataclass, field
from typing import Literal

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import User
from app.core.tenancy.context import get_current_tenant


@dataclass
class DataScope:
    scope_type: Literal["all", "staff", "lister", "customer"]
    user_id: uuid.UUID
    lister_ids: list[uuid.UUID] = field(default_factory=list)

    @property
    def owner_ids(self) -> list[uuid.UUID]:
        if self.scope_type == "all":
            return []
        if self.scope_type == "staff":
            return [self.user_id, *self.lister_ids]
        if self.scope_type == "lister":
            return [self.user_id]
        return []

    @property
    def is_scoped(self) -> bool:
        return self.scope_type != "all"


async def resolve_data_scope(session: AsyncSession, user: User) -> DataScope:
    if user.user_type == "admin":
        return DataScope(scope_type="all", user_id=user.id)

    if user.user_type == "customer":
        return DataScope(scope_type="customer", user_id=user.id)

    tenant_ctx = get_current_tenant()
    isolation_mode = "shared"
    if tenant_ctx and tenant_ctx.tenant.config:
        isolation_mode = tenant_ctx.tenant.config.get("staff_isolation_mode", "shared")

    if user.user_type == "lister":
        return DataScope(scope_type="lister", user_id=user.id)

    # user_type == "staff"
    if isolation_mode == "shared":
        return DataScope(scope_type="all", user_id=user.id)

    result = await session.exec(
        select(User.id).where(
            User.manager_id == user.id,
            User.user_type == "lister",
            User.is_active == True,
        )
    )
    lister_ids = list(result.all())
    return DataScope(scope_type="staff", user_id=user.id, lister_ids=lister_ids)
