from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import TENANT_AUTH_TABLES  # noqa: F401 — registers models
from app.core.auth.seed import seed_default_roles
from app.core.notifications.models import TENANT_NOTIFICATION_TABLES  # noqa: F401
from app.core.tenancy.context import validate_schema_name
from app.domains.bookings.models import TENANT_BOOKING_TABLES  # noqa: F401
from app.domains.resources.models import TENANT_RESOURCE_TABLES  # noqa: F401
from app.domains.reviews.models import TENANT_REVIEW_TABLES  # noqa: F401

TENANT_TABLE_REGISTRY: set[str] = set()
TENANT_TABLE_REGISTRY.update(TENANT_AUTH_TABLES)
TENANT_TABLE_REGISTRY.update(TENANT_RESOURCE_TABLES)
TENANT_TABLE_REGISTRY.update(TENANT_BOOKING_TABLES)
TENANT_TABLE_REGISTRY.update(TENANT_REVIEW_TABLES)
TENANT_TABLE_REGISTRY.update(TENANT_NOTIFICATION_TABLES)


async def create_tenant_tables(engine: AsyncEngine, schema_name: str) -> None:
    validate_schema_name(schema_name)
    tables = [
        t for t in SQLModel.metadata.sorted_tables if t.name in TENANT_TABLE_REGISTRY
    ]
    async with engine.begin() as conn:
        await conn.execute(text(f"SET search_path TO {schema_name}"))
        for table in tables:
            await conn.run_sync(lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True))
        await conn.execute(text("SET search_path TO public"))


async def provision_tenant_schema(
    engine: AsyncEngine, session: AsyncSession, tenant_id: str
) -> str:
    schema_name = f"tenant_{tenant_id.replace('-', '_')}"
    validate_schema_name(schema_name)
    await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    await session.commit()
    await create_tenant_tables(engine, schema_name)

    await session.execute(text(f"SET search_path TO {schema_name}, public"))
    await seed_default_roles(session)
    await session.execute(text("SET search_path TO public"))

    return schema_name
