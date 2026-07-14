from fastapi import APIRouter, Query
from sqlmodel import select

from app import database as db_module
from app import logging
from app.core.admin.models import TenantTheme
from app.core.admin.schemas import ThemeResponse
from app.core.tenancy.context import get_current_tenant
from app.core.tenancy.models import Tenant, TenantDomain

router = APIRouter(prefix="/api/tenancy", tags=["tenancy"])


@router.get("/resolve")
async def resolve_tenant(domain: str = Query(...)):
    try:
        async with db_module.async_session_factory() as session:
            result = await session.exec(select(TenantDomain).where(TenantDomain.domain == domain))
            tenant_domain = result.first()
            if tenant_domain is None:
                return None

            result = await session.exec(
                select(Tenant).where(Tenant.id == tenant_domain.tenant_id, Tenant.is_active.is_(True))
            )
            tenant = result.first()
            if tenant is None:
                return None

            return {
                "tenant_id": str(tenant.id),
                "slug": tenant.slug,
                "schema_name": tenant.schema_name,
                "name": tenant.name,
                "landing_page": (tenant.config or {}).get("landing_page", "browse"),
            }
    except Exception as error:
        logging.log("resolve_tenant", {"EVENT": "resolve_tenant_error", "ERROR": error})
        return None


@router.get("/theme", response_model=ThemeResponse)
async def get_public_theme():
    ctx = get_current_tenant()
    async with db_module.async_session_factory() as session:
        result = await session.exec(
            select(TenantTheme).where(TenantTheme.tenant_id == ctx.tenant.id)
        )
        theme = result.first()
        if theme is None:
            theme = TenantTheme(tenant_id=ctx.tenant.id)
            session.add(theme)
            await session.commit()
            await session.refresh(theme)
        return ThemeResponse.model_validate(theme)
