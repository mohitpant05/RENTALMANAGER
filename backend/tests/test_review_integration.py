import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.tenancy.models import Tenant
from app.domains.bookings.models import Booking


@pytest.fixture
async def review_resource_type(client: AsyncClient, admin_headers: dict) -> dict:
    resp = await client.post(
        "/api/resource-types/",
        json={
            "name": "Review Test Venues",
            "slug": "review-test-venues",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
            "attribute_schema": [],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def review_resource(
    client: AsyncClient, admin_headers: dict, review_resource_type: dict
) -> dict:
    resp = await client.post(
        "/api/resources/",
        json={
            "type_id": review_resource_type["id"],
            "name": "Review Test Villa",
            "description": "A place to review",
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
async def completed_booking(
    db_session: AsyncSession,
    review_resource: dict,
    customer_headers: dict,
    client: AsyncClient,
    test_tenant: Tenant,
) -> Booking:
    resp = await client.get("/api/auth/me", headers=customer_headers)
    assert resp.status_code == 200
    customer_id = resp.json()["id"]

    await db_session.execute(
        text(f"SET search_path TO {test_tenant.schema_name}, public")
    )
    booking = Booking(
        resource_id=uuid.UUID(review_resource["id"]),
        user_id=uuid.UUID(customer_id),
        status="completed",
        start_time=datetime.now(UTC) - timedelta(days=3),
        end_time=datetime.now(UTC) - timedelta(days=1),
        total_price=200.0,
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)
    return booking


@pytest.fixture
async def second_completed_booking(
    db_session: AsyncSession,
    review_resource: dict,
    customer_headers: dict,
    client: AsyncClient,
    test_tenant: Tenant,
) -> Booking:
    resp = await client.get("/api/auth/me", headers=customer_headers)
    customer_id = resp.json()["id"]

    await db_session.execute(
        text(f"SET search_path TO {test_tenant.schema_name}, public")
    )
    booking = Booking(
        resource_id=uuid.UUID(review_resource["id"]),
        user_id=uuid.UUID(customer_id),
        status="completed",
        start_time=datetime.now(UTC) - timedelta(days=6),
        end_time=datetime.now(UTC) - timedelta(days=4),
        total_price=300.0,
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)
    return booking


@pytest.mark.asyncio
async def test_create_review(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    resp = await client.post(
        "/api/reviews/",
        json={
            "booking_id": str(completed_booking.id),
            "rating": 5,
            "title": "Amazing stay",
            "body": "Would definitely come back",
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 5
    assert data["direction"] == "customer_to_resource"
    assert data["resource_id"] == str(completed_booking.resource_id)


@pytest.mark.asyncio
async def test_create_review_with_categories(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    resp = await client.post(
        "/api/reviews/",
        json={
            "booking_id": str(completed_booking.id),
            "rating": 4,
            "category_ratings": {"cleanliness": 5, "location": 3},
        },
        headers=customer_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["category_ratings"]["cleanliness"] == 5
    assert data["category_ratings"]["location"] == 3


@pytest.mark.asyncio
async def test_create_review_duplicate_fails(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 4},
        headers=customer_headers,
    )
    resp = await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 3},
        headers=customer_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_review_non_completed_booking_fails(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
    review_resource: dict,
    test_tenant: Tenant,
):
    resp = await client.get("/api/auth/me", headers=customer_headers)
    customer_id = resp.json()["id"]

    await db_session.execute(
        text(f"SET search_path TO {test_tenant.schema_name}, public")
    )
    booking = Booking(
        resource_id=uuid.UUID(review_resource["id"]),
        user_id=uuid.UUID(customer_id),
        status="confirmed",
        start_time=datetime.now(UTC) + timedelta(days=1),
        end_time=datetime.now(UTC) + timedelta(days=3),
        total_price=200.0,
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)

    resp = await client.post(
        "/api/reviews/",
        json={"booking_id": str(booking.id), "rating": 5},
        headers=customer_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_reviews_for_resource(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 4},
        headers=customer_headers,
    )
    resp = await client.get(
        f"/api/reviews/?resource_id={completed_booking.resource_id}",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["resource_id"] == str(completed_booking.resource_id)


@pytest.mark.asyncio
async def test_list_my_reviews(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 5},
        headers=customer_headers,
    )
    resp = await client.get("/api/reviews/my", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_get_review(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    resp = await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 4},
        headers=customer_headers,
    )
    review_id = resp.json()["id"]
    resp = await client.get(f"/api/reviews/{review_id}", headers=customer_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == review_id


@pytest.mark.asyncio
async def test_moderate_review(
    client: AsyncClient,
    customer_headers: dict,
    admin_headers: dict,
    completed_booking: Booking,
):
    resp = await client.post(
        "/api/reviews/",
        json={
            "booking_id": str(completed_booking.id),
            "rating": 1,
            "body": "Terrible",
        },
        headers=customer_headers,
    )
    review_id = resp.json()["id"]

    resp = await client.post(
        f"/api/reviews/{review_id}/moderate",
        json={"status": "flagged", "reason": "Potential spam"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "flagged"


@pytest.mark.asyncio
async def test_rating_summary(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 4},
        headers=customer_headers,
    )
    resp = await client.get(
        f"/api/reviews/resource/{completed_booking.resource_id}/summary",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["average"] == 4.0
    assert data["count"] == 1


@pytest.mark.asyncio
async def test_resource_rating_updated_after_review(
    client: AsyncClient, customer_headers: dict, completed_booking: Booking
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 5},
        headers=customer_headers,
    )
    resp = await client.get(
        f"/api/resources/{completed_booking.resource_id}",
        headers=customer_headers,
    )
    assert resp.status_code == 200
    resource = resp.json()
    assert resource["rating_avg"] == 5.0
    assert resource["rating_count"] == 1


@pytest.mark.asyncio
async def test_rating_avg_with_multiple_reviews(
    client: AsyncClient,
    customer_headers: dict,
    completed_booking: Booking,
    second_completed_booking: Booking,
):
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(completed_booking.id), "rating": 4},
        headers=customer_headers,
    )
    await client.post(
        "/api/reviews/",
        json={"booking_id": str(second_completed_booking.id), "rating": 2},
        headers=customer_headers,
    )
    resp = await client.get(
        f"/api/reviews/resource/{completed_booking.resource_id}/summary",
        headers=customer_headers,
    )
    data = resp.json()
    assert data["average"] == 3.0
    assert data["count"] == 2
