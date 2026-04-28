from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.core.auth.router import router as auth_router
from app.core.search.router import router as search_router
from app.core.tenancy.middleware import TenantMiddleware
from app.database import engine
from app.domains.bookings.router import router as booking_router
from app.domains.resources.router import resource_router, resource_type_router
from app.domains.reviews.router import router as review_router


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

app.add_middleware(TenantMiddleware)
app.include_router(auth_router)
app.include_router(resource_type_router)
app.include_router(resource_router)
app.include_router(booking_router)
app.include_router(search_router)
app.include_router(review_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
