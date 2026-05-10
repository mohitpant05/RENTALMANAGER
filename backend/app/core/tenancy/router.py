from fastapi import APIRouter, Query
from sqlmodel import select

from app import database as db_module
from app.core.tenancy.models import Tenant, TenantDomain

router = APIRouter(prefix="/api/tenancy", tags=["tenancy"])


@router.get("/resolve")
async def resolve_tenant(domain: str = Query(...)):
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
        }
