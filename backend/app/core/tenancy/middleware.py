import logging
import re
import uuid

from fastapi import Request
from sqlmodel import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app import database as db_module
from app.core.logging import clear_request_context, set_request_context
from app.core.tenancy.context import TenantContext, set_current_tenant
from app.core.tenancy.models import Tenant, TenantDomain

logger = logging.getLogger("app.tenancy.middleware")

TENANT_FREE_PATHS = {
    "/api/health", "/api/docs", "/api/openapi.json", "/api/redoc", "/api/tenancy/resolve",
}
TENANT_FREE_PREFIXES = (
    "/api/platform/", "/api/health/", "/api/currency/", "/api/payments/webhook/",
    "/api/storage/proxy/",
)


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Set request-scoped context for log correlation
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        set_request_context(req_id, request.url.path)

        path = request.url.path
        method = request.method
        logger.info("INCOMING %s %s [tenant-header=%s] [host=%s]",
                     method, path,
                     request.headers.get("X-Tenant-ID", "(none)"),
                     request.headers.get("host", "(none)"))

        if path in TENANT_FREE_PATHS or not path.startswith("/api"):
            logger.debug("Tenant-free path (%s) — skipping tenant resolution", path)
            set_current_tenant(None)
            response = await call_next(request)
            clear_request_context()
            return response

        if any(path.startswith(p) for p in TENANT_FREE_PREFIXES):
            logger.debug("Tenant-free prefix (%s) — skipping tenant resolution", path)
            set_current_tenant(None)
            response = await call_next(request)
            clear_request_context()
            return response

        tenant = await self._resolve_tenant(request)
        if tenant is None:
            logger.warning("Tenant NOT FOUND for %s %s", method, path)
            clear_request_context()
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Tenant not found. Provide X-Tenant-ID header."
                },
            )

        logger.info("Tenant resolved: slug=%s id=%s schema=%s",
                     tenant.slug, tenant.id, tenant.schema_name)
        set_current_tenant(TenantContext(tenant=tenant, schema_name=tenant.schema_name))
        response = await call_next(request)
        set_current_tenant(None)
        clear_request_context()
        return response

    async def _resolve_tenant(self, request: Request) -> Tenant | None:
        # Step 1: X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            logger.debug("Resolving by X-Tenant-ID header: %s", tenant_id)
            return await self._get_tenant_by_slug(tenant_id)

        # Step 2: Subdomain
        host = request.headers.get("host", "")
        subdomain = self._extract_subdomain(host)
        if subdomain:
            logger.debug("Resolving by subdomain: %s (from host: %s)", subdomain, host)
            return await self._get_tenant_by_slug(subdomain)

        # Step 3: Custom domain
        domain = host.split(":")[0]
        logger.debug("Resolving by custom domain: %s", domain)
        return await self._get_tenant_by_domain(domain)

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
        # Skip subdomain extraction for IP addresses
        if re.match(r"^\d+\.\d+\.\d+\.\d+$", host_without_port):
            return None
        parts = host_without_port.split(".")
        if len(parts) >= 3:
            return parts[0]
        return None

    async def _get_tenant_by_slug(self, slug: str) -> Tenant | None:
        if not re.match(r"^[a-zA-Z0-9_-]+$", slug):
            logger.debug("_get_tenant_by_slug: invalid slug format '%s'", slug)
            return None
        async with db_module.async_session_factory() as session:
            result = await session.exec(
                select(Tenant).where(Tenant.slug == slug, Tenant.is_active.is_(True))
            )
            tenant = result.first()
            if tenant:
                logger.debug("_get_tenant_by_slug: found tenant id=%s slug=%s schema=%s",
                             tenant.id, tenant.slug, tenant.schema_name)
            else:
                logger.debug("_get_tenant_by_slug: no active tenant with slug='%s'", slug)
            return tenant

    async def _get_tenant_by_domain(self, domain: str) -> Tenant | None:
        async with db_module.async_session_factory() as session:
            result = await session.exec(
                select(TenantDomain).where(TenantDomain.domain == domain)
            )
            tenant_domain = result.first()
            if tenant_domain is None:
                logger.debug("_get_tenant_by_domain: no TenantDomain record for '%s'", domain)
                return None
            logger.debug("_get_tenant_by_domain: found TenantDomain tenant_id=%s",
                            tenant_domain.tenant_id)

            result = await session.exec(
                select(Tenant).where(
                    Tenant.id == tenant_domain.tenant_id, Tenant.is_active.is_(True)
                )
            )
            tenant = result.first()
            if tenant:
                logger.debug("_get_tenant_by_domain: found tenant id=%s slug=%s",
                             tenant.id, tenant.slug)
            else:
                logger.debug("_get_tenant_by_domain: tenant not active or not found")
            return tenant
