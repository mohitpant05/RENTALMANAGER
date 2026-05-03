from contextlib import asynccontextmanager

import asyncio

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.core.admin.platform_router import router as platform_router
from app.core.admin.router import router as admin_router
from app.core.auth.router import router as auth_router
from app.core.notifications.router import router as notification_router
from app.core.search.router import router as search_router
from app.core.storage.router import router as storage_router
from app.core.tenancy.middleware import TenantMiddleware
from app.database import async_session_factory, engine
from app.domains.bookings.router import router as booking_router
from app.domains.resources.router import resource_router, resource_type_router
from app.domains.reviews.router import router as review_router
from app.redis_client import get_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting RentManager backend (debug={settings.debug})")
    yield
    await engine.dispose()
    print("Shutting down RentManager backend")


app = FastAPI(
    title="RentManager API",
    version="0.1.0",
    lifespan=lifespan,
)

origins = ["http://localhost:3000", "http://localhost"]

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TenantMiddleware)
app.include_router(auth_router)
app.include_router(resource_type_router)
app.include_router(resource_router)
app.include_router(booking_router)
app.include_router(search_router)
app.include_router(review_router)
app.include_router(notification_router)
app.include_router(storage_router)
app.include_router(admin_router)
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
