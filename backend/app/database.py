import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session as SyncSession
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.core.tenancy.context import get_current_tenant, validate_schema_name

logger = logging.getLogger("app.database")

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


@event.listens_for(SyncSession, "after_begin")
def _set_search_path_on_begin(session, transaction, _connection):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        return
    schema = tenant_ctx.schema_name
    validate_schema_name(schema)
    logger.info("[after_begin] setting search_path to %s", schema)
    _connection.execute(text(f"SET search_path TO {schema}, public"))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def get_tenant_session(tenant_schema: str) -> AsyncGenerator[AsyncSession, None]:
    validate_schema_name(tenant_schema)
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
        logger.info("get_db: no tenant context — using default search_path")
        async with async_session_factory() as session:
            yield session
        return
    logger.info("get_db: setting search_path=%s for tenant=%s",
                 tenant_ctx.schema_name, tenant_ctx.tenant.slug)
    async with async_session_factory() as session:
        await session.execute(
            text(f"SET search_path TO {tenant_ctx.schema_name}, public")
        )
        logger.debug("get_db: search_path set to %s, public", tenant_ctx.schema_name)
        yield session
        await session.execute(text("SET search_path TO public"))
        logger.debug("get_db: search_path reset to public")
