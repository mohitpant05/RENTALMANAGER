import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.notifications.service import notify
from app.core.tenancy.models import Tenant


@pytest.fixture
async def user_notification(
    db_session: AsyncSession,
    customer_headers: dict,
    client: AsyncClient,
    test_tenant: Tenant,
):
    resp = await client.get("/api/auth/me", headers=customer_headers)
    customer_id = resp.json()["id"]

    await db_session.execute(
        text(f"SET search_path TO {test_tenant.schema_name}, public")
    )
    n = await notify(
        db_session,
        uuid.UUID(customer_id),
        "booking.confirmed",
        "Booking Confirmed",
        "Your booking for Beach Villa has been confirmed",
        payload={"booking_id": "test-123", "resource_name": "Beach Villa"},
    )
    return n


@pytest.mark.asyncio
async def test_list_notifications(
    client: AsyncClient, customer_headers: dict, user_notification
):
    resp = await client.get("/api/notifications/", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["event_type"] == "booking.confirmed"


@pytest.mark.asyncio
async def test_list_unread_only(
    client: AsyncClient, customer_headers: dict, user_notification
):
    resp = await client.get(
        "/api/notifications/?unread_only=true", headers=customer_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(not n["is_read"] for n in data)


@pytest.mark.asyncio
async def test_unread_count(
    client: AsyncClient, customer_headers: dict, user_notification
):
    resp = await client.get(
        "/api/notifications/unread-count", headers=customer_headers
    )
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


@pytest.mark.asyncio
async def test_mark_read(
    client: AsyncClient, customer_headers: dict, user_notification
):
    notification_id = str(user_notification.id)
    resp = await client.post(
        f"/api/notifications/{notification_id}/read", headers=customer_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None


@pytest.mark.asyncio
async def test_mark_read_other_user_fails(
    client: AsyncClient, admin_headers: dict, user_notification
):
    notification_id = str(user_notification.id)
    resp = await client.post(
        f"/api/notifications/{notification_id}/read", headers=admin_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mark_all_read(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
    test_tenant: Tenant,
):
    resp = await client.get("/api/auth/me", headers=customer_headers)
    customer_id = resp.json()["id"]

    await db_session.execute(
        text(f"SET search_path TO {test_tenant.schema_name}, public")
    )
    for i in range(3):
        await notify(
            db_session,
            uuid.UUID(customer_id),
            "booking.confirmed",
            f"Notification {i}",
            f"Body {i}",
        )

    resp = await client.post(
        "/api/notifications/read-all", headers=customer_headers
    )
    assert resp.status_code == 200
    assert resp.json()["marked"] >= 3

    resp = await client.get(
        "/api/notifications/unread-count", headers=customer_headers
    )
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_notification_not_found(client: AsyncClient, customer_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/notifications/{fake_id}/read", headers=customer_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_notification_payload_preserved(
    client: AsyncClient, customer_headers: dict, user_notification
):
    resp = await client.get("/api/notifications/", headers=customer_headers)
    data = resp.json()
    notification = next(
        (n for n in data if n["id"] == str(user_notification.id)), None
    )
    assert notification is not None
    assert notification["payload"]["booking_id"] == "test-123"
    assert notification["payload"]["resource_name"] == "Beach Villa"
