import re

from fastapi import Request
from sqlmodel import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.database import async_session_factory
from app.core.tenancy.context import TenantContext, set_current_tenant
from app.core.tenancy.models import Tenant, TenantDomain

TENANT_FREE_PATHS = {"/api/health", "/api/docs", "/api/openapi.json", "/api/redoc"}


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in TENANT_FREE_PATHS or not path.startswith("/api"):
            set_current_tenant(None)
            return await call_next(request)

        tenant = await self._resolve_tenant(request)
        if tenant is None:
            return JSONResponse(
                status_code=400,
                content={"detail": "Tenant not found. Provide X-Tenant-ID header or use tenant subdomain."},
            )

        set_current_tenant(TenantContext(tenant=tenant, schema_name=tenant.schema_name))
        response = await call_next(request)
        set_current_tenant(None)
        return response

    async def _resolve_tenant(self, request: Request) -> Tenant | None:
        # 1. Check X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return await self._get_tenant_by_slug(tenant_id)

        # 2. Check subdomain
        host = request.headers.get("host", "")
        subdomain = self._extract_subdomain(host)
        if subdomain:
            return await self._get_tenant_by_slug(subdomain)

        # 3. Check custom domain
        domain = host.split(":")[0]
        return await self._get_tenant_by_domain(domain)

    def _extract_subdomain(self, host: str) -> str | None:
        host_without_port = host.split(":")[0]
        parts = host_without_port.split(".")
        if len(parts) >= 3:
            return parts[0]
        return None

    async def _get_tenant_by_slug(self, slug: str) -> Tenant | None:
        if not re.match(r"^[a-zA-Z0-9_-]+$", slug):
            return None
        async with async_session_factory() as session:
            result = await session.exec(
                select(Tenant).where(Tenant.slug == slug, Tenant.is_active == True)
            )
            return result.first()

    async def _get_tenant_by_domain(self, domain: str) -> Tenant | None:
        async with async_session_factory() as session:
            result = await session.exec(
                select(TenantDomain).where(TenantDomain.domain == domain)
            )
            tenant_domain = result.first()
            if tenant_domain is None:
                return None

            result = await session.exec(
                select(Tenant).where(Tenant.id == tenant_domain.tenant_id, Tenant.is_active == True)
            )
            return result.first()
