"""
Seed development environment with platform user, tenant, and admin user.
Run: docker compose exec backend python scripts/seed_dev.py
"""
import asyncio
from uuid import uuid4

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import PlatformUser, Role, User, UserRole
from app.core.tenancy.models import Tenant
from app.core.tenancy.provisioning import provision_tenant_schema

DB_URL = "postgresql+asyncpg://rentmanager:rentmanager_dev@postgres:5432/rentmanager"

PLATFORM_EMAIL = "platform@rentmanager.dev"
PLATFORM_PASSWORD = "platform123"
TENANT_NAME = "Demo Rentals"
TENANT_SLUG = "demo"
ADMIN_EMAIL = "admin@rentmanager.dev"
ADMIN_PASSWORD = "admin123"


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


async def seed():
    engine = create_async_engine(DB_URL, echo=False)

    async with AsyncSession(engine) as session:
        # 1. Platform user
        existing = (await session.exec(
            select(PlatformUser).where(PlatformUser.email == PLATFORM_EMAIL)
        )).first()
        if existing:
            print(f"Platform user already exists: {PLATFORM_EMAIL}")
        else:
            pu = PlatformUser(
                id=uuid4(),
                email=PLATFORM_EMAIL,
                password_hash=hash_pw(PLATFORM_PASSWORD),
                full_name="Platform Admin",
            )
            session.add(pu)
            await session.commit()
            print(f"Created platform user: {PLATFORM_EMAIL}")

        # 2. Tenant
        existing_tenant = (await session.exec(
            select(Tenant).where(Tenant.slug == TENANT_SLUG)
        )).first()
        if existing_tenant:
            tenant = existing_tenant
            schema_name = str(tenant.schema_name)
            print(f"Tenant already exists: {TENANT_SLUG} (schema: {schema_name})")
        else:
            tenant_id = uuid4()
            schema_name = f"tenant_{str(tenant_id).replace('-', '_')}"
            tenant = Tenant(
                id=tenant_id,
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                schema_name=schema_name,
                base_currency="USD",
                timezone="UTC",
            )
            session.add(tenant)
            await session.commit()
            await provision_tenant_schema(engine, session, str(tenant_id))
            print(f"Created tenant: {TENANT_SLUG} (schema: {schema_name})")

        # 3. Admin user in tenant schema
        await session.execute(text(f"SET search_path TO {schema_name}, public"))

        existing_user = (await session.exec(
            select(User).where(User.email == ADMIN_EMAIL)
        )).first()
        if existing_user:
            print(f"Admin user already exists: {ADMIN_EMAIL}")
        else:
            user = User(
                id=uuid4(),
                email=ADMIN_EMAIL,
                password_hash=hash_pw(ADMIN_PASSWORD),
                full_name="Demo Admin",
                is_active=True,
                is_verified=True,
                user_type="admin",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            admin_role = (await session.exec(
                select(Role).where(Role.slug == "admin")
            )).first()
            if admin_role:
                session.add(UserRole(user_id=user.id, role_id=admin_role.id))
                await session.commit()

            print(f"Created admin user: {ADMIN_EMAIL}")

        await session.execute(text("SET search_path TO public"))

    await engine.dispose()

    print("\n" + "=" * 55)
    print("  DEV CREDENTIALS")
    print("=" * 55)
    print(f"  Platform:  {PLATFORM_EMAIL} / {PLATFORM_PASSWORD}")
    print(f"  Tenant:    {TENANT_SLUG}")
    print(f"  Admin:     {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print("=" * 55)
    print()
    print("  Curl test:")
    print(f'  curl -s http://localhost/api/auth/login \\')
    print(f'    -H "Content-Type: application/json" \\')
    print(f'    -H "X-Tenant-ID: {TENANT_SLUG}" \\')
    print(f'    -d \'{{"email":"{ADMIN_EMAIL}","password":"{ADMIN_PASSWORD}"}}\'')
    print()


if __name__ == "__main__":
    asyncio.run(seed())
