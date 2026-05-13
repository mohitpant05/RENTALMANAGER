import pytest
from httpx import ASGITransport, AsyncClient

from app.core.admin.platform_auth import create_platform_token
from app.core.auth.models import PlatformUser
from app.core.auth.password import hash_password
from app.main import app


@pytest.fixture
async def platform_token(db_session):
    user = PlatformUser(
        email="superadmin@test.com",
        password_hash=hash_password("superpass123"),
        full_name="Super Admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return create_platform_token(str(user.id))


@pytest.fixture
async def platform_client(db_engine):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_dashboard_stats(platform_client, platform_token, test_tenant):
    resp = await platform_client.get(
        "/api/platform/dashboard/stats",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tenants" in data
    assert "active_tenants" in data
    assert data["total_tenants"] >= 1


@pytest.mark.asyncio
async def test_dashboard_stats_unauthenticated(platform_client):
    resp = await platform_client.get("/api/platform/dashboard/stats")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_platform_settings_crud(platform_client, platform_token):
    resp = await platform_client.get(
        "/api/platform/settings",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = await platform_client.put(
        "/api/platform/settings/test_key",
        json={"value": "test_value", "description": "A test setting"},
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["key"] == "test_key"
    assert resp.json()["value"] == "test_value"

    resp = await platform_client.get(
        "/api/platform/settings",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_validate_secret_key_correct(platform_client):
    from app.config import get_settings

    key = get_settings().superadmin_secret_key
    resp = await platform_client.post(
        "/api/platform/validate-key",
        json={"key": key},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


@pytest.mark.asyncio
async def test_validate_secret_key_wrong(platform_client):
    resp = await platform_client.post(
        "/api/platform/validate-key",
        json={"key": "wrong-key"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_tenant_theme_endpoints(platform_client, platform_token, test_tenant):
    resp = await platform_client.get(
        f"/api/platform/tenants/{test_tenant.id}/theme",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 404

    resp = await platform_client.put(
        f"/api/platform/tenants/{test_tenant.id}/theme",
        json={"colors": {"primary": "#ff0000"}},
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["colors"]["primary"] == "#ff0000"

    resp = await platform_client.get(
        f"/api/platform/tenants/{test_tenant.id}/theme",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["colors"]["primary"] == "#ff0000"
