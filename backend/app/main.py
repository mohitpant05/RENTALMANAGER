import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.core.admin.ip_middleware import SuperadminIPMiddleware
from app.core.admin.platform_router import router as platform_router
from app.core.admin.roles_router import router as roles_router
from app.core.admin.router import router as admin_router
from app.core.auth.router import router as auth_router
from app.core.commission.router import router as commission_router
from app.core.currency.router import router as currency_router
from app.core.notifications.router import router as notification_router
from app.core.payments.router import router as payment_router
from app.core.payouts.router import router as payout_router
from app.core.search.router import router as search_router
from app.core.storage.router import router as storage_router
from app.core.tenancy.middleware import TenantMiddleware
from app.core.tenancy.router import router as tenancy_router
from app.database import async_session_factory, engine
from app.domains.bookings.router import router as booking_router
from app.domains.resources.router import resource_router, resource_type_router
from app.domains.reviews.router import router as review_router
from app.rate_limiter import limiter
from app.redis_client import get_redis

settings = get_settings()


async def _sync_template_schemas():
    from sqlalchemy import text as sa_text
    from sqlmodel import select

    from app.core.tenancy.context import validate_schema_name
    from app.core.tenancy.models import Tenant
    from app.domains.resources.models import ResourceType
    from app.domains.resources.templates import RESOURCE_TYPE_TEMPLATES

    async with async_session_factory() as session:
        result = await session.exec(
            select(Tenant).where(Tenant.is_active.is_(True))
        )
        tenants = list(result.all())

    for tenant in tenants:
        validate_schema_name(tenant.schema_name)
        async with async_session_factory() as session:
            await session.execute(
                sa_text(f"SET search_path TO {tenant.schema_name}, public")
            )
            result = await session.exec(select(ResourceType))
            resource_types = list(result.all())

            for rt in resource_types:
                tmpl = RESOURCE_TYPE_TEMPLATES.get(rt.slug)
                if not tmpl:
                    continue
                tmpl_schema = tmpl.get("attribute_schema")
                if tmpl_schema and rt.attribute_schema != tmpl_schema:
                    rt.attribute_schema = tmpl_schema
                    session.add(rt)

            await session.commit()
            await session.execute(sa_text("SET search_path TO public"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure logging AFTER uvicorn's dictConfig so our handlers stick
    _reconfigure_logging()
    _log = logging.getLogger("app.main")
    _log.info("Starting RentManager backend (debug=%s)", settings.debug)
    try:
        await _sync_template_schemas()
    except Exception as e:
        _log.warning("Template schema sync skipped: %s", e)
    yield
    await engine.dispose()
    _log.info("Shutting down RentManager backend")


def _reconfigure_logging() -> None:
    root = logging.getLogger()
    # Remove existing uvicorn handlers to avoid duplicates
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    # Also ensure SQLAlchemy engine logs are visible
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


app = FastAPI(
    title="RentManager API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

origins = [
    "http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:3003", "http://localhost",
    "http://192.168.29.245", "http://192.168.29.245:3000",
]

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TenantMiddleware)
app.add_middleware(
    SuperadminIPMiddleware,
    allowed_ips=settings.allowed_superadmin_ips,
)
app.include_router(tenancy_router)
app.include_router(auth_router)
app.include_router(resource_type_router)
app.include_router(resource_router)
app.include_router(booking_router)
app.include_router(search_router)
app.include_router(review_router)
app.include_router(notification_router)
app.include_router(storage_router)
app.include_router(admin_router)
app.include_router(roles_router)
app.include_router(currency_router)
app.include_router(commission_router)
app.include_router(payment_router)
app.include_router(payout_router)
app.include_router(platform_router)


async def _ping_postgres() -> dict:
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar_one()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def _ping_redis() -> dict:
    try:
        r = get_redis()
        await r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def _ping_meilisearch() -> dict:
    try:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{settings.meili_url}/health", timeout=3.0
            )
            resp.raise_for_status()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def _ping_minio() -> dict:
    try:
        from app.core.storage.client import get_minio_client

        client = get_minio_client()
        await asyncio.get_event_loop().run_in_executor(
            None, client.list_buckets
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/health/postgres")
async def health_postgres():
    return await _ping_postgres()


@app.get("/api/health/redis")
async def health_redis():
    return await _ping_redis()


@app.get("/api/health/meilisearch")
async def health_meilisearch():
    return await _ping_meilisearch()


@app.get("/api/health/minio")
async def health_minio():
    return await _ping_minio()


@app.get("/api/health/all")
async def health_all():
    results = {
        "postgres": await _ping_postgres(),
        "redis": await _ping_redis(),
        "meilisearch": await _ping_meilisearch(),
        "minio": await _ping_minio(),
    }
    all_ok = all(r["status"] == "ok" for r in results.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "version": "0.1.0",
        "services": results,
    }
