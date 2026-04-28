import time

import pytest
from httpx import AsyncClient


@pytest.fixture
async def search_venue_type(client: AsyncClient, admin_headers: dict) -> dict:
    resp = await client.post(
        "/api/resource-types/",
        json={
            "name": "Search Test Venues",
            "slug": "search-test-venues",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
            "attribute_schema": [
                {"name": "bedrooms", "type": "number", "required": True, "filterable": True},
                {"name": "pet_friendly", "type": "boolean", "required": False, "filterable": True},
            ],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def indexed_resource(
    client: AsyncClient, admin_headers: dict, search_venue_type: dict
) -> dict:
    resp = await client.post(
        "/api/resources/",
        json={
            "type_id": search_venue_type["id"],
            "name": "Seaside Villa",
            "description": "Beautiful villa by the sea",
            "base_price": 200.0,
            "location_lat": 40.7128,
            "location_lng": -74.0060,
            "location_address": "123 Ocean Dr",
            "attributes": {"bedrooms": 3, "pet_friendly": True},
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
    time.sleep(1)
    return resp.json()


@pytest.mark.asyncio
async def test_search_basic(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "Seaside",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_total_hits"] >= 1
    assert any(h["id"] == indexed_resource["id"] for h in data["hits"])


@pytest.mark.asyncio
async def test_search_with_filter(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "",
            "filters": {"bedrooms": {"min": 2}},
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_total_hits"] >= 1


@pytest.mark.asyncio
async def test_search_with_geo(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "",
            "geo_lat": 40.71,
            "geo_lng": -74.01,
            "geo_radius_km": 10,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_total_hits"] >= 1


@pytest.mark.asyncio
async def test_search_no_results(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "xyznonexistent123",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_total_hits"] == 0
    assert data["hits"] == []


@pytest.mark.asyncio
async def test_search_sort_by_price(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "",
            "sort_by": "base_price",
            "sort_order": "desc",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["estimated_total_hits"] >= 1


@pytest.mark.asyncio
async def test_search_without_tenant_fails(client: AsyncClient):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "venues",
            "q": "test",
        },
    )
    assert resp.status_code in (400, 401)
