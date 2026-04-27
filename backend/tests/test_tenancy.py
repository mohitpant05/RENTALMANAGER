import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_without_tenant_header_to_tenant_endpoint(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_invalid_tenant_slug_rejected(client: AsyncClient):
    response = await client.get(
        "/api/resources",
        headers={"X-Tenant-ID": "'; DROP TABLE tenants;--"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_nonexistent_tenant_returns_400(client: AsyncClient):
    response = await client.get(
        "/api/resources",
        headers={"X-Tenant-ID": "nonexistent-tenant"},
    )
    assert response.status_code == 400
