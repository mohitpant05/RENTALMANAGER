"""
Create a test user for local development.
Run: docker compose exec backend python scripts/create_test_user.py
Or: cd backend && uv run python scripts/create_test_user.py
"""
import asyncio
from uuid import uuid4

import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


async def create_test_user():
    # Database URL from docker-compose
    db_url = "postgresql+asyncpg://rentmanager:rentmanager_dev@localhost:5432/rentmanager"

    engine = create_async_engine(db_url, echo=True)

    # Create tables if not exist (import all models)
    from app.core.auth.models import User
    from app.core.tenancy.models import Tenant

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(engine) as session:
        # Check if test user already exists
        result = await session.exec(
            select(User).where(User.email == "test@rentmanager.local")
        )
        existing = result.first()

        if existing:
            print("Test user already exists: test@rentmanager.local")
            print("Password: testpassword123")
            await session.close()
            return

        # Get first tenant for assignment
        result = await session.exec(select(Tenant).limit(1))
        tenant = result.first()

        if not tenant:
            print("No tenant found. Please create a tenant first.")
            await session.close()
            return

        # Create test user
        user = User(
            id=uuid4(),
            email="test@rentmanager.local",
            password_hash=hash_password("testpassword123"),
            full_name="Test User",
            phone=None,
            is_active=True,
            is_verified=True,
            user_type="admin",  # admin to have full access
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        print("=" * 50)
        print("TEST USER CREATED SUCCESSFULLY")
        print("=" * 50)
        print("Email:    test@rentmanager.local")
        print("Password: testpassword123")
        print(f"User ID: {user.id}")
        print(f"Tenant:   {tenant.name} (slug: {tenant.slug})")
        print("=" * 50)
        print("\nUse these credentials to login at: http://localhost:3000/login")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_test_user())
