import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from sqlalchemy import text

from app.config import get_settings
from app.core.tenancy.models import Tenant
from app.core.tenancy.provisioning import create_tenant_tables
from app.core.tenancy.context import TenantContext, set_current_tenant
from app.database import engine
from app.main import app

settings = get_settings()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def tenant_slug() -> str:
    return f"test-tenant-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> AsyncGenerator[Tenant, None]:
    tenant_id = uuid.uuid4()
    schema_name = f"tenant_test_{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        id=tenant_id,
        name="Test Tenant",
        slug=f"test-{uuid.uuid4().hex[:8]}",
        schema_name=schema_name,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    await db_session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    await db_session.commit()
    await create_tenant_tables(engine, schema_name)

    set_current_tenant(TenantContext(tenant=tenant, schema_name=schema_name))
    yield tenant
    set_current_tenant(None)

    await db_session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
    await db_session.commit()
