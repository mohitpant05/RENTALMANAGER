from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print(f"Starting RentManager backend (debug={settings.debug})")
    yield
    print("Shutting down RentManager backend")


app = FastAPI(
    title="RentManager API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
