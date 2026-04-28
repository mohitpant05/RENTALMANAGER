import re
from contextvars import ContextVar
from dataclasses import dataclass

from app.core.tenancy.models import Tenant

_SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def validate_schema_name(name: str) -> str:
    if not _SCHEMA_RE.match(name):
        raise ValueError(f"Invalid schema name: {name!r}")
    return name


@dataclass
class TenantContext:
    tenant: Tenant
    schema_name: str

    def __post_init__(self) -> None:
        validate_schema_name(self.schema_name)


_tenant_ctx: ContextVar[TenantContext | None] = ContextVar("tenant_ctx", default=None)


def get_current_tenant() -> TenantContext | None:
    return _tenant_ctx.get()


def set_current_tenant(ctx: TenantContext | None) -> None:
    _tenant_ctx.set(ctx)
