import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import User
from app.core.auth.password import hash_password
from app.core.tenancy.models import Tenant
from app.domains.resources.models import Resource, ResourceType
from app.main import app


@pytest.fixture
async def setup_bundled(
    db_session: AsyncSession, test_tenant: Tenant, db_engine
) -> dict:
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    admin = User(
        email="bundleadmin@test.com",
        password_hash=hash_password("adminpass123"),
        full_name="Bundle Admin",
        user_type="admin",
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    venue_type = ResourceType(
        name="Venues",
        slug="venues",
        availability_model="date_range",
        pricing_model="fixed_per_day",
        role="primary",
    )
    cook_type = ResourceType(
        name="Cooks",
        slug="cooks",
        availability_model="date_range",
        pricing_model="fixed_per_day",
        role="addon",
        discovery_radius_km=50.0,
    )
    db_session.add(venue_type)
    db_session.add(cook_type)
    await db_session.commit()
    await db_session.refresh(venue_type)
    await db_session.refresh(cook_type)

    venue = Resource(
        type_id=venue_type.id,
        name="Mountain Lodge",
        base_price=5000,
        currency="INR",
        status="active",
        location_lat=30.0869,
        location_lng=78.2676,
        owner_id=admin.id,
    )
    cook = Resource(
        type_id=cook_type.id,
        name="Chef Rajesh",
        base_price=1500,
        currency="INR",
        status="active",
        location_lat=30.1,
        location_lng=78.3,
        owner_id=admin.id,
    )
    db_session.add(venue)
    db_session.add(cook)
    await db_session.commit()
    await db_session.refresh(venue)
    await db_session.refresh(cook)
    await db_session.execute(text("SET search_path TO public"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        resp = await client.post(
            "/api/auth/login",
            json={"email": "bundleadmin@test.com", "password": "adminpass123"},
            headers={"X-Tenant-ID": test_tenant.slug},
        )
        tokens = resp.json()
        headers = {
            "X-Tenant-ID": test_tenant.slug,
            "Authorization": f"Bearer {tokens['access_token']}",
        }

        yield {
            "client": client,
            "headers": headers,
            "venue": venue,
            "cook": cook,
            "tenant": test_tenant,
        }


@pytest.mark.asyncio
async def test_addon_discovery(setup_bundled):
    ctx = setup_bundled
    resp = await ctx["client"].get(
        f"/api/resources/{ctx['venue'].id}/addons",
        params={"start_date": "2026-06-01T00:00:00Z", "end_date": "2026-06-05T00:00:00Z"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "cooks" in data
    cooks = data["cooks"]["resources"]
    assert len(cooks) >= 1
    assert cooks[0]["name"] == "Chef Rajesh"


@pytest.mark.asyncio
async def test_bundled_booking_flow(setup_bundled):
    ctx = setup_bundled
    headers = ctx["headers"]
    client = ctx["client"]
    venue_id = str(ctx["venue"].id)
    cook_id = str(ctx["cook"].id)

    # Hold venue
    venue_hold = await client.post(
        f"/api/resources/{venue_id}/availability/hold",
        json={"start": "2026-06-01T00:00:00Z", "end": "2026-06-05T00:00:00Z"},
        headers=headers,
    )
    assert venue_hold.status_code == 200
    venue_token = venue_hold.json()["hold_token"]

    # Hold cook
    cook_hold = await client.post(
        f"/api/resources/{cook_id}/availability/hold",
        json={"start": "2026-06-01T00:00:00Z", "end": "2026-06-05T00:00:00Z"},
        headers=headers,
    )
    assert cook_hold.status_code == 200
    cook_token = cook_hold.json()["hold_token"]

    # Create bundled booking
    resp = await client.post(
        "/api/bookings/bundled",
        json={
            "primary": {
                "resource_id": venue_id,
                "hold_token": venue_token,
                "start_time": "2026-06-01T00:00:00Z",
                "end_time": "2026-06-05T00:00:00Z",
            },
            "addons": [
                {
                    "resource_id": cook_id,
                    "hold_token": cook_token,
                    "start_time": "2026-06-01T00:00:00Z",
                    "end_time": "2026-06-05T00:00:00Z",
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["primary"]["booking_group_id"] is not None
    assert len(data["addons"]) == 1
    assert data["addons"][0]["parent_booking_id"] == data["primary"]["id"]
    assert data["addons"][0]["booking_group_id"] == data["primary"]["booking_group_id"]
