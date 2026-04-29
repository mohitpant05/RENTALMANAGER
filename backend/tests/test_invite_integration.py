import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.auth.invite import get_invite_data, store_invite_token
from app.core.auth.models import User
from app.core.tenancy.models import Tenant


@pytest.mark.asyncio
async def test_invite_staff_creates_inactive_user(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={
            "email": "newstaff@test.com",
            "full_name": "New Staff",
            "role_slugs": ["staff"],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newstaff@test.com"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_verify_invite_valid_token(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant, db_session
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "verify@test.com", "full_name": "Verify User"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    from app.redis_client import get_redis

    r = get_redis()
    keys = []
    async for key in r.scan_iter(match="invite:*"):
        keys.append(key)
    assert len(keys) >= 1
    token = keys[-1].replace("invite:", "")

    resp = await client.get(
        f"/api/auth/verify-invite?token={token}",
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["email"] == "verify@test.com"
    assert data["full_name"] == "Verify User"


@pytest.mark.asyncio
async def test_verify_invite_invalid_token(
    client: AsyncClient, test_tenant: Tenant
):
    resp = await client.get(
        "/api/auth/verify-invite?token=nonexistent-token",
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is False


@pytest.mark.asyncio
async def test_accept_invite_activates_user_and_returns_tokens(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "accept@test.com", "full_name": "Accept User"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    from app.redis_client import get_redis

    r = get_redis()
    keys = []
    async for key in r.scan_iter(match="invite:*"):
        keys.append(key)
    token = keys[-1].replace("invite:", "")

    resp = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "password": "newpassword123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "accept@test.com", "password": "newpassword123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_accept_invite_token_single_use(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "singleuse@test.com", "full_name": "Single Use"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    from app.redis_client import get_redis

    r = get_redis()
    keys = []
    async for key in r.scan_iter(match="invite:*"):
        keys.append(key)
    token = keys[-1].replace("invite:", "")

    resp = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "password": "password123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp.status_code == 200

    resp2 = await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "password": "password123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_reinvite_active_user_fails(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "reinvite@test.com", "full_name": "Reinvite User"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    from app.redis_client import get_redis

    r = get_redis()
    keys = []
    async for key in r.scan_iter(match="invite:*"):
        keys.append(key)
    token = keys[-1].replace("invite:", "")

    await client.post(
        "/api/auth/accept-invite",
        json={"token": token, "password": "password123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )

    resp2 = await client.post(
        "/api/admin/staff",
        json={"email": "reinvite@test.com", "full_name": "Reinvite User"},
        headers=admin_headers,
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_pending_invite_returns_403(
    client: AsyncClient, admin_headers: dict, test_tenant: Tenant
):
    resp = await client.post(
        "/api/admin/staff",
        json={"email": "pending@test.com", "full_name": "Pending User"},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    login_resp = await client.post(
        "/api/auth/login",
        json={"email": "pending@test.com", "password": "anything"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert login_resp.status_code == 403
    assert "pending invite" in login_resp.json()["detail"].lower()
