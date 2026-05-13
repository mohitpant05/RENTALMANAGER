from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.core.tenancy.models import Tenant


@pytest.mark.asyncio
async def test_create_resource_type(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/resource-types/",
        json={
            "name": "Apartments",
            "slug": "apartments",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
            "attribute_schema": [
                {"name": "bedrooms", "type": "number", "required": True, "filterable": True},
                {"name": "amenities", "type": "tags", "required": False, "filterable": True},
            ],
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Apartments"
    assert data["slug"] == "apartments"
    assert data["availability_model"] == "date_range"
    assert data["is_active"] is True
    assert len(data["attribute_schema"]) == 2


@pytest.mark.asyncio
async def test_create_resource_type_duplicate_slug(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/resource-types/",
        json={
            "name": "Boats",
            "slug": "boats",
            "availability_model": "hourly",
            "pricing_model": "per_hour",
        },
        headers=admin_headers,
    )
    response = await client.post(
        "/api/resource-types/",
        json={
            "name": "Boats Again",
            "slug": "boats",
            "availability_model": "hourly",
            "pricing_model": "per_hour",
        },
        headers=admin_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_resource_type_requires_admin(
    client: AsyncClient, customer_headers: dict
):
    response = await client.post(
        "/api/resource-types/",
        json={
            "name": "Test",
            "slug": "test-no-perm",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
        },
        headers=customer_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_resource_types(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/resource-types/",
        json={
            "name": "Cars",
            "slug": "cars",
            "availability_model": "hourly",
            "pricing_model": "per_hour",
        },
        headers=admin_headers,
    )
    response = await client.get(
        "/api/resource-types/",
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    slugs = [t["slug"] for t in data]
    assert "cars" in slugs


@pytest.mark.asyncio
async def test_get_resource_type_by_slug(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/resource-types/",
        json={
            "name": "Villas",
            "slug": "villas",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
        },
        headers=admin_headers,
    )
    response = await client.get(
        "/api/resource-types/villas",
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "villas"


@pytest.mark.asyncio
async def test_update_resource_type(client: AsyncClient, admin_headers: dict):
    create = await client.post(
        "/api/resource-types/",
        json={
            "name": "Offices",
            "slug": "offices",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
        },
        headers=admin_headers,
    )
    rt_id = create.json()["id"]
    response = await client.put(
        f"/api/resource-types/{rt_id}",
        json={"name": "Office Spaces", "icon": "building"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Office Spaces"
    assert response.json()["icon"] == "building"


@pytest.mark.asyncio
async def test_delete_resource_type(client: AsyncClient, admin_headers: dict):
    create = await client.post(
        "/api/resource-types/",
        json={
            "name": "Temp Type",
            "slug": "temp-type",
            "availability_model": "hourly",
            "pricing_model": "per_hour",
        },
        headers=admin_headers,
    )
    rt_id = create.json()["id"]
    response = await client.delete(
        f"/api/resource-types/{rt_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_create_from_template(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/resource-types/from-template/venues",
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "venues"
    assert data["availability_model"] == "date_range"
    assert data["pricing_model"] == "fixed_per_day"
    assert data["attribute_schema"] is not None
    assert len(data["attribute_schema"]) >= 4


@pytest.mark.asyncio
async def test_create_from_template_not_found(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/resource-types/from-template/nonexistent",
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient, test_tenant: Tenant):
    response = await client.get(
        "/api/resource-types/templates",
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert response.status_code == 200
    data = response.json()
    assert "venues" in data
    assert "vehicles" in data
    assert "cooks" in data


# --- Resource CRUD Tests ---

@pytest.fixture
async def venue_type_id(client: AsyncClient, admin_headers: dict) -> str:
    resp = await client.post(
        "/api/resource-types/from-template/venues",
        headers=admin_headers,
    )
    if resp.status_code == 409:
        get_resp = await client.get(
            "/api/resource-types/venues",
            headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
        )
        return get_resp.json()["id"]
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_resource(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    response = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Beach House",
            "description": "Beautiful beachfront property",
            "base_price": 150.0,
            "attributes": {
                "property_type": "house",
                "bedrooms": 3,
                "bathrooms": 2,
                "max_guests": 6,
                "amenities": ["wifi", "pool", "parking"],
            },
            "location_lat": 25.7617,
            "location_lng": -80.1918,
            "location_address": "123 Beach Rd, Miami, FL",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Beach House"
    assert data["base_price"] == 150.0
    assert data["status"] == "draft"
    assert data["attributes"]["bedrooms"] == 3


@pytest.mark.asyncio
async def test_create_resource_invalid_attributes(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    response = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Bad Attrs",
            "base_price": 100.0,
            "attributes": {
                "property_type": "spaceship",
                "bedrooms": "many",
                "bathrooms": 1,
                "max_guests": 4,
            },
        },
        headers=admin_headers,
    )
    assert response.status_code == 422
    assert "attribute_errors" in response.json()["detail"]


    @pytest.mark.asyncio
    async def test_list_resources(
        client: AsyncClient, admin_headers: dict, venue_type_id: str
    ):
        resp = await client.post(
            "/api/resources/",
            json={
                "type_id": venue_type_id,
                "name": "Mountain Cabin",
                "base_price": 200.0,
                "attributes": {
                    "property_type": "house",
                    "bedrooms": 2,
                    "bathrooms": 1,
                    "max_guests": 4,
                },
            },
            headers=admin_headers,
        )
        resource_id = resp.json()["id"]
        await client.put(
            f"/api/resources/{resource_id}",
            json={"status": "active"},
            headers=admin_headers,
        )
        response = await client.get(
            "/api/resources/",
            params={"type_id": venue_type_id},
            headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1


@pytest.mark.asyncio
async def test_update_resource(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    create = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Old Name",
            "base_price": 100.0,
            "attributes": {
                "property_type": "apartment",
                "bedrooms": 1,
                "bathrooms": 1,
                "max_guests": 2,
            },
        },
        headers=admin_headers,
    )
    resource_id = create.json()["id"]
    response = await client.put(
        f"/api/resources/{resource_id}",
        json={"name": "New Name", "base_price": 120.0, "status": "active"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["base_price"] == 120.0
    assert data["status"] == "active"
    assert data["version"] == 2


@pytest.mark.asyncio
async def test_delete_resource(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    create = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Temp Resource",
            "base_price": 50.0,
            "attributes": {
                "property_type": "studio",
                "bedrooms": 0,
                "bathrooms": 1,
                "max_guests": 1,
            },
        },
        headers=admin_headers,
    )
    resource_id = create.json()["id"]
    response = await client.delete(
        f"/api/resources/{resource_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204

    get_resp = await client.get(
        f"/api/resources/{resource_id}",
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert get_resp.json()["status"] == "archived"


# --- Availability + Pricing Tests ---

@pytest.fixture
async def active_venue(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
) -> dict:
    create = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Test Venue",
            "base_price": 100.0,
            "attributes": {
                "property_type": "apartment",
                "bedrooms": 2,
                "bathrooms": 1,
                "max_guests": 4,
            },
        },
        headers=admin_headers,
    )
    resource_id = create.json()["id"]
    await client.put(
        f"/api/resources/{resource_id}",
        json={"status": "active"},
        headers=admin_headers,
    )
    return {"id": resource_id, "base_price": 100.0}


@pytest.mark.asyncio
async def test_check_availability(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=10)).isoformat()
    end = (now + timedelta(days=13)).isoformat()
    response = await client.post(
        f"/api/resources/{active_venue['id']}/availability/check",
        json={"start": start, "end": end},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["price"] == 300.0


@pytest.mark.asyncio
async def test_hold_resource(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=20)).isoformat()
    end = (now + timedelta(days=22)).isoformat()
    response = await client.post(
        f"/api/resources/{active_venue['id']}/availability/hold",
        json={"start": start, "end": end, "hold_minutes": 10},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "hold_token" in data
    assert data["price"] == 200.0


@pytest.mark.asyncio
async def test_hold_then_check_unavailable(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=30)).isoformat()
    end = (now + timedelta(days=32)).isoformat()

    hold = await client.post(
        f"/api/resources/{active_venue['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    assert hold.status_code == 200

    check = await client.post(
        f"/api/resources/{active_venue['id']}/availability/check",
        json={"start": start, "end": end},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert check.status_code == 200
    assert check.json()["available"] is False


@pytest.mark.asyncio
async def test_hold_then_release_then_available(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=40)).isoformat()
    end = (now + timedelta(days=42)).isoformat()

    hold = await client.post(
        f"/api/resources/{active_venue['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    token = hold.json()["hold_token"]

    release = await client.post(
        f"/api/resources/{active_venue['id']}/availability/release",
        json={"hold_token": token},
        headers=admin_headers,
    )
    assert release.status_code == 200

    check = await client.post(
        f"/api/resources/{active_venue['id']}/availability/check",
        json={"start": start, "end": end},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert check.json()["available"] is True


@pytest.mark.asyncio
async def test_calculate_price(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=50)).isoformat()
    end = (now + timedelta(days=55)).isoformat()
    response = await client.post(
        f"/api/resources/{active_venue['id']}/price",
        json={"start": start, "end": end},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 500.0
    assert data["currency"] == "USD"


@pytest.mark.asyncio
async def test_hold_inactive_resource_fails(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    create = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Inactive Place",
            "base_price": 75.0,
            "attributes": {
                "property_type": "apartment",
                "bedrooms": 1,
                "bathrooms": 1,
                "max_guests": 2,
            },
        },
        headers=admin_headers,
    )
    resource_id = create.json()["id"]
    now = datetime.now(UTC)
    start = (now + timedelta(days=60)).isoformat()
    end = (now + timedelta(days=62)).isoformat()
    response = await client.post(
        f"/api/resources/{resource_id}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    assert response.status_code == 400
