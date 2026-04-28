import uuid

import pytest
from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.platform_auth import create_platform_token
from app.core.auth.models import PlatformUser
from app.core.auth.password import hash_password
from app.core.tenancy.models import Tenant


@pytest.fixture
async def platform_headers(db_session: AsyncSession) -> dict:
    user = PlatformUser(
        email="superadmin@platform.com",
        password_hash=hash_password("platformpass"),
        full_name="Super Admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_platform_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_tenant_info(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/admin/tenant", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
    assert "slug" in data


@pytest.mark.asyncio
async def test_patch_tenant_config(client: AsyncClient, admin_headers: dict):
    resp = await client.patch(
        "/api/admin/tenant",
        json={"name": "Updated Tenant", "base_currency": "EUR"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Tenant"
    assert resp.json()["base_currency"] == "EUR"


@pytest.mark.asyncio
async def test_get_and_update_theme(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/admin/theme", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["brand"] == {}

    resp = await client.put(
        "/api/admin/theme",
        json={
            "brand": {"name": "CityRentals", "logo_url": "/logo.svg"},
            "colors": {"primary": "#2563eb", "secondary": "#7c3aed"},
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["brand"]["name"] == "CityRentals"
    assert resp.json()["colors"]["primary"] == "#2563eb"


@pytest.mark.asyncio
async def test_domain_crud(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/admin/domains",
        json={"domain": "rentals.example.com", "is_primary": True},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    domain_id = resp.json()["id"]
    assert resp.json()["domain"] == "rentals.example.com"

    resp = await client.get("/api/admin/domains", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client.delete(
        f"/api/admin/domains/{domain_id}", headers=admin_headers
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_duplicate_domain_fails(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/admin/domains",
        json={"domain": "unique-domain.com"},
        headers=admin_headers,
    )
    resp = await client.post(
        "/api/admin/domains",
        json={"domain": "unique-domain.com"},
        headers=admin_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_staff_invite_and_list(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/admin/staff",
        json={
            "email": "newstaff@test.com",
            "full_name": "New Staff",
            "password": "staffpass1",
            "user_type": "staff",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "newstaff@test.com"
    assert resp.json()["user_type"] == "staff"

    resp = await client.get("/api/admin/staff", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_staff_deactivate(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/admin/staff",
        json={
            "email": "deactivate-me@test.com",
            "full_name": "To Deactivate",
            "password": "pass123",
        },
        headers=admin_headers,
    )
    user_id = resp.json()["id"]

    resp = await client.post(
        f"/api/admin/staff/{user_id}/deactivate", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_customer_cannot_access_admin(
    client: AsyncClient, customer_headers: dict
):
    resp = await client.get("/api/admin/tenant", headers=customer_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_platform_login(client: AsyncClient, db_session: AsyncSession):
    user = PlatformUser(
        email="login-test@platform.com",
        password_hash=hash_password("secret123"),
        full_name="Platform Admin",
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/platform/login",
        json={"email": "login-test@platform.com", "password": "secret123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_platform_list_tenants(
    client: AsyncClient, platform_headers: dict, test_tenant: Tenant
):
    resp = await client.get("/api/platform/tenants", headers=platform_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_platform_create_tenant(
    client: AsyncClient, platform_headers: dict, db_engine
):
    slug = f"new-tenant-{uuid.uuid4().hex[:6]}"
    resp = await client.post(
        "/api/platform/tenants",
        json={"name": "New Tenant", "slug": slug},
        headers=platform_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == slug
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_platform_deactivate_tenant(
    client: AsyncClient, platform_headers: dict, test_tenant: Tenant
):
    tenant_id = str(test_tenant.id)
    resp = await client.post(
        f"/api/platform/tenants/{tenant_id}/deactivate",
        headers=platform_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_platform_login_invalid_credentials(client: AsyncClient):
    resp = await client.post(
        "/api/platform/login",
        json={"email": "nobody@x.com", "password": "wrong"},
    )
    assert resp.status_code == 401
