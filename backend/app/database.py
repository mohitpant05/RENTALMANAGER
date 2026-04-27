from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from sqlmodel import SQLModel

from app.config import get_settings
from app.core.tenancy.context import get_current_tenant

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_tenant_session(tenant_schema: str) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        await session.execute(text(f"SET search_path TO {tenant_schema}, public"))
        yield session
        await session.execute(text("SET search_path TO public"))


async def create_tenant_schema(session: AsyncSession, tenant_id: str) -> None:
    schema_name = f"tenant_{tenant_id.replace('-', '_')}"
    await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    await session.commit()


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        async with async_session_factory() as session:
            yield session
        return
    async with async_session_factory() as session:
        await session.execute(
            text(f"SET search_path TO {tenant_ctx.schema_name}, public")
        )
        yield session
        await session.execute(text("SET search_path TO public"))
