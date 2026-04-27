from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.core.auth.router import router as auth_router
from app.core.tenancy.middleware import TenantMiddleware
from app.database import engine


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


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
