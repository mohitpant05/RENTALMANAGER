import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

import app.database as db_module
from app.config import get_settings
from app.core.auth.models import User
from app.core.auth.password import hash_password
from app.core.auth.seed import seed_default_roles
from app.core.tenancy.context import TenantContext, set_current_tenant
from app.core.tenancy.models import Tenant
from app.core.tenancy.provisioning import create_tenant_tables
from app.main import app
from app.redis_client import get_redis

settings = get_settings()


@pytest.fixture
async def db_engine():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    original_engine = db_module.engine
    original_factory = db_module.async_session_factory
    db_module.engine = engine
    db_module.async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    yield engine
    db_module.engine = original_engine
    db_module.async_session_factory = original_factory
    get_redis.cache_clear()
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


@pytest.fixture
def tenant_slug() -> str:
    return f"test-tenant-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def test_tenant(db_session: AsyncSession, db_engine) -> AsyncGenerator[Tenant, None]:
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
    await create_tenant_tables(db_engine, schema_name)

    await db_session.execute(text(f"SET search_path TO {schema_name}, public"))
    await seed_default_roles(db_session)
    await db_session.execute(text("SET search_path TO public"))

    set_current_tenant(TenantContext(tenant=tenant, schema_name=schema_name))
    yield tenant
    set_current_tenant(None)

    await db_session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
    await db_session.commit()


@pytest.fixture
async def admin_headers(client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession) -> dict:
    schema_name = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema_name}, public"))
    admin = User(
        email="admin@test.com",
        password_hash=hash_password("adminpass123"),
        full_name="Test Admin",
        user_type="admin",
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.execute(text("SET search_path TO public"))

    resp = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "adminpass123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    tokens = resp.json()
    return {
        "X-Tenant-ID": test_tenant.slug,
        "Authorization": f"Bearer {tokens['access_token']}",
    }


@pytest.fixture
async def customer_headers(client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession) -> dict:
    schema_name = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema_name}, public"))
    customer = User(
        email="customer@test.com",
        password_hash=hash_password("customerpass1"),
        full_name="Test Customer",
        user_type="customer",
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    await db_session.execute(text("SET search_path TO public"))

    resp = await client.post(
        "/api/auth/login",
        json={"email": "customer@test.com", "password": "customerpass1"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    tokens = resp.json()
    return {
        "X-Tenant-ID": test_tenant.slug,
        "Authorization": f"Bearer {tokens['access_token']}",
    }
