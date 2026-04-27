from contextvars import ContextVar
from dataclasses import dataclass

from app.core.tenancy.models import Tenant


@dataclass
class TenantContext:
    tenant: Tenant
    schema_name: str


_tenant_ctx: ContextVar[TenantContext | None] = ContextVar("tenant_ctx", default=None)


def get_current_tenant() -> TenantContext | None:
    return _tenant_ctx.get()


def set_current_tenant(ctx: TenantContext | None) -> None:
    _tenant_ctx.set(ctx)
