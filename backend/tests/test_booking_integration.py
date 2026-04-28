from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.fixture
async def venue_type(client: AsyncClient, admin_headers: dict) -> dict:
    resp = await client.post(
        "/api/resource-types/",
        json={
            "name": "Booking Test Venues",
            "slug": "booking-test-venues",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
            "cancellation_defaults": {
                "free_cancel_hours": 48,
                "partial_cancel_hours": 24,
                "partial_refund_percent": 50,
                "no_refund_after": True,
            },
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def active_resource(
    client: AsyncClient, admin_headers: dict, venue_type: dict
) -> dict:
    resp = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type["id"],
            "name": "Booking Test Apartment",
            "base_price": 100.0,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    resource = resp.json()

    resp = await client.put(
        f"/api/resources/{resource['id']}",
        json={"status": "active"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
async def held_resource(
    client: AsyncClient, admin_headers: dict, active_resource: dict
) -> dict:
    now = datetime.now(UTC)
    start = (now + timedelta(days=5)).isoformat()
    end = (now + timedelta(days=8)).isoformat()

    resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    hold_data = resp.json()
    return {
        "resource_id": active_resource["id"],
        "hold_token": hold_data["hold_token"],
        "start_time": start,
        "end_time": end,
    }


@pytest.mark.asyncio
async def test_create_booking_auto_confirm(
    client: AsyncClient, admin_headers: dict, held_resource: dict
):
    resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": held_resource["resource_id"],
            "hold_token": held_resource["hold_token"],
            "start_time": held_resource["start_time"],
            "end_time": held_resource["end_time"],
            "auto_confirm": True,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    booking = resp.json()
    assert booking["status"] == "confirmed"
    assert booking["confirmed_at"] is not None
    assert booking["total_price"] == 300.0


@pytest.mark.asyncio
async def test_create_booking_manual_confirm(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=15)).isoformat()
    end = (now + timedelta(days=17)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    assert hold_resp.status_code == 200
    hold_token = hold_resp.json()["hold_token"]

    resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": False,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    booking = resp.json()
    assert booking["status"] == "pending"
    assert booking["confirmed_at"] is None


@pytest.mark.asyncio
async def test_create_booking_invalid_hold_token(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=20)).isoformat()
    end = (now + timedelta(days=22)).isoformat()

    resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": "invalid-token-does-not-exist",
            "start_time": start,
            "end_time": end,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "hold" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_confirm_pending_booking(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=25)).isoformat()
    end = (now + timedelta(days=27)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": False,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/confirm",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_reject_pending_booking(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=30)).isoformat()
    end = (now + timedelta(days=32)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": False,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/reject",
        json={"reason": "Not available"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["cancellation_reason"] == "Not available"


@pytest.mark.asyncio
async def test_cancel_booking_with_full_refund(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=35)).isoformat()
    end = (now + timedelta(days=37)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": True,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/cancel",
        json={"reason": "Changed plans"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["refund_percent"] == 100.0
    assert data["cancellation_reason"] == "Changed plans"


@pytest.mark.asyncio
async def test_cancel_booking_no_refund(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(hours=10)).isoformat()
    end = (now + timedelta(hours=34)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": True,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/cancel",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["refund_percent"] == 0.0


@pytest.mark.asyncio
async def test_cannot_confirm_already_confirmed(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=40)).isoformat()
    end = (now + timedelta(days=42)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": True,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/confirm",
        headers=admin_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_bookings(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=45)).isoformat()
    end = (now + timedelta(days=47)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
        },
        headers=admin_headers,
    )

    resp = await client.get("/api/bookings", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_get_booking_by_id(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=50)).isoformat()
    end = (now + timedelta(days=52)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/bookings/{booking_id}", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == booking_id


@pytest.mark.asyncio
async def test_customer_cannot_confirm_booking(
    client: AsyncClient, customer_headers: dict, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=55)).isoformat()
    end = (now + timedelta(days=57)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": False,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/confirm",
        headers=customer_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_cleanup_expired_holds(db_session, test_tenant, db_engine):
    import uuid
    from sqlalchemy import text
    from app.core.auth.models import User
    from app.core.auth.password import hash_password
    from app.domains.resources.models import ResourceAvailability, ResourceType, Resource
    from app.domains.bookings.tasks import cleanup_expired_holds

    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    # Create a real user so the owner_id FK constraint is satisfied
    owner = User(
        email="tasktest@test.com",
        password_hash=hash_password("testpass123"),
        full_name="Task Test Owner",
        user_type="admin",
    )
    db_session.add(owner)
    await db_session.commit()
    await db_session.refresh(owner)

    rt = ResourceType(
        name="Task Test", slug="task-test-rt",
        availability_model="date_range", pricing_model="fixed_per_day",
    )
    db_session.add(rt)
    await db_session.commit()
    await db_session.refresh(rt)

    resource = Resource(
        type_id=rt.id, name="Task Test Res",
        base_price=50.0, owner_id=owner.id, status="active",
    )
    db_session.add(resource)
    await db_session.commit()
    await db_session.refresh(resource)

    expired_hold = ResourceAvailability(
        resource_id=resource.id,
        start_time=datetime.now(UTC) + timedelta(days=1),
        end_time=datetime.now(UTC) + timedelta(days=2),
        status="held",
        hold_token="expired-token",
        hold_expires=datetime.now(UTC) - timedelta(minutes=5),
    )
    db_session.add(expired_hold)
    await db_session.commit()

    count = await cleanup_expired_holds(db_session)
    assert count == 1

    await db_session.execute(text("SET search_path TO public"))
