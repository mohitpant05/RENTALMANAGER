
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import Permission, Role, User
from app.core.auth.password import hash_password
from app.core.auth.schemas import LoginRequest, RegisterRequest
from app.core.auth.seed import seed_default_roles
from app.core.auth.service import authenticate_user, register_user
from app.core.tenancy.models import Tenant


@pytest.mark.asyncio
async def test_register_user_creates_user(db_session: AsyncSession, test_tenant: Tenant):
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    req = RegisterRequest(
        email="new@example.com",
        password="strongpass123",
        full_name="New User",
    )
    user = await register_user(db_session, req, tenant_id=str(test_tenant.id))
    assert user.email == "new@example.com"
    assert user.user_type == "customer"
    assert user.password_hash != "strongpass123"


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(db_session: AsyncSession, test_tenant: Tenant):
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    req = RegisterRequest(
        email="dup@example.com",
        password="strongpass123",
        full_name="First User",
    )
    await register_user(db_session, req, tenant_id=str(test_tenant.id))

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await register_user(db_session, req, tenant_id=str(test_tenant.id))
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_authenticate_user_valid(db_session: AsyncSession, test_tenant: Tenant):
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    user = User(
        email="auth@example.com",
        password_hash=hash_password("mypassword123"),
        full_name="Auth User",
        user_type="customer",
    )
    db_session.add(user)
    await db_session.commit()

    req = LoginRequest(email="auth@example.com", password="mypassword123")
    result = await authenticate_user(db_session, req)
    assert result.email == "auth@example.com"


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(db_session: AsyncSession, test_tenant: Tenant):
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    user = User(
        email="wrong@example.com",
        password_hash=hash_password("correctpass1"),
        full_name="Wrong Pass User",
        user_type="customer",
    )
    db_session.add(user)
    await db_session.commit()

    from fastapi import HTTPException

    req = LoginRequest(email="wrong@example.com", password="incorrectpass")
    with pytest.raises(HTTPException) as exc_info:
        await authenticate_user(db_session, req)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_register_endpoint(client: AsyncClient, test_tenant: Tenant):
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "strongpass123",
            "full_name": "New User",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_endpoint(client: AsyncClient, test_tenant: Tenant):
    await client.post(
        "/api/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "strongpass123",
            "full_name": "Login User",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )

    response = await client.post(
        "/api/auth/login",
        json={
            "email": "loginuser@example.com",
            "password": "strongpass123",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_tenant: Tenant):
    await client.post(
        "/api/auth/register",
        json={
            "email": "wronglogin@example.com",
            "password": "strongpass123",
            "full_name": "Wrong Login",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )

    response = await client.post(
        "/api/auth/login",
        json={
            "email": "wronglogin@example.com",
            "password": "wrongpassword1",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient, test_tenant: Tenant):
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "meuser@example.com",
            "password": "strongpass123",
            "full_name": "Me User",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    token = reg.json()["access_token"]

    response = await client.get(
        "/api/auth/me",
        headers={
            "X-Tenant-ID": test_tenant.slug,
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "meuser@example.com"
    assert data["user_type"] == "customer"


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient, test_tenant: Tenant):
    response = await client.get(
        "/api/auth/me",
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_endpoint(client: AsyncClient, test_tenant: Tenant):
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "refreshuser@example.com",
            "password": "strongpass123",
            "full_name": "Refresh User",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    refresh_token = reg.json()["refresh_token"]

    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_logout_endpoint(client: AsyncClient, test_tenant: Tenant):
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "logoutuser@example.com",
            "password": "strongpass123",
            "full_name": "Logout User",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    tokens = reg.json()
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    response = await client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh},
        headers={
            "X-Tenant-ID": test_tenant.slug,
            "Authorization": f"Bearer {access}",
        },
    )
    assert response.status_code == 200

    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_seed_default_roles(db_session: AsyncSession, test_tenant: Tenant):
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    await seed_default_roles(db_session)

    result = await db_session.exec(select(Role).where(Role.is_system))
    roles = result.all()
    role_slugs = {r.slug for r in roles}
    assert "admin" in role_slugs
    assert "staff" in role_slugs
    assert "customer" in role_slugs
    assert "lister" in role_slugs


@pytest.mark.asyncio
async def test_seed_creates_permissions(db_session: AsyncSession, test_tenant: Tenant):
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    await seed_default_roles(db_session)

    result = await db_session.exec(select(Permission))
    perms = result.all()
    codenames = {p.codename for p in perms}
    assert "resources:*:read" in codenames
    assert "bookings:*:create" in codenames


@pytest.mark.asyncio
async def test_seed_is_idempotent(db_session: AsyncSession, test_tenant: Tenant):
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    await seed_default_roles(db_session)
    await seed_default_roles(db_session)

    result = await db_session.exec(select(Role))
    roles = result.all()
    slugs = [r.slug for r in roles]
    assert slugs.count("admin") == 1


@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient, test_tenant: Tenant):
    headers = {"X-Tenant-ID": test_tenant.slug}

    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "flow@example.com",
            "password": "strongpass123",
            "full_name": "Flow User",
        },
        headers=headers,
    )
    assert reg.status_code == 201
    tokens = reg.json()

    me = await client.get(
        "/api/auth/me",
        headers={**headers, "Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "flow@example.com"

    refresh = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )
    assert refresh.status_code == 200
    new_tokens = refresh.json()
    assert new_tokens["access_token"] != tokens["access_token"]

    stale = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )
    assert stale.status_code == 401

    logout = await client.post(
        "/api/auth/logout",
        json={"refresh_token": new_tokens["refresh_token"]},
        headers={**headers, "Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert logout.status_code == 200


@pytest.mark.asyncio
async def test_cross_tenant_token_rejected(client: AsyncClient, test_tenant: Tenant):
    headers = {"X-Tenant-ID": test_tenant.slug}
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": "cross@example.com",
            "password": "strongpass123",
            "full_name": "Cross Tenant",
        },
        headers=headers,
    )
    token = reg.json()["access_token"]

    response = await client.get(
        "/api/auth/me",
        headers={
            "X-Tenant-ID": "nonexistent-tenant",
            "Authorization": f"Bearer {token}",
        },
    )
    assert response.status_code in (400, 403)
