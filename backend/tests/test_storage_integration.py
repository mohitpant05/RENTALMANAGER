import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_upload_url(client: AsyncClient, admin_headers: dict):
    resp = await client.post(
        "/api/storage/upload-url",
        json={
            "entity_type": "resource",
            "entity_id": str(uuid.uuid4()),
            "file_name": "test-photo.jpg",
            "mime_type": "image/jpeg",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "upload_url" in data
    assert "file_path" in data
    assert data["file_path"].startswith("resource/")
    assert "bucket" in data


@pytest.mark.asyncio
async def test_confirm_upload_and_list(client: AsyncClient, admin_headers: dict):
    entity_id = str(uuid.uuid4())

    upload_resp = await client.post(
        "/api/storage/upload-url",
        json={
            "entity_type": "resource",
            "entity_id": entity_id,
            "file_name": "villa.jpg",
            "mime_type": "image/jpeg",
        },
        headers=admin_headers,
    )
    file_path = upload_resp.json()["file_path"]

    resp = await client.post(
        "/api/storage/confirm",
        json={
            "file_path": file_path,
            "file_name": "villa.jpg",
            "mime_type": "image/jpeg",
            "file_size": 5000,
            "entity_type": "resource",
            "entity_id": entity_id,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"] == "villa.jpg"
    assert data["file_size"] == 5000
    assert data["download_url"] is not None

    resp = await client.get(
        f"/api/storage/attachments?entity_type=resource&entity_id={entity_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    attachments = resp.json()
    assert len(attachments) >= 1
    assert attachments[0]["file_name"] == "villa.jpg"


@pytest.mark.asyncio
async def test_get_attachment(client: AsyncClient, admin_headers: dict):
    entity_id = str(uuid.uuid4())

    upload_resp = await client.post(
        "/api/storage/upload-url",
        json={
            "entity_type": "resource",
            "entity_id": entity_id,
            "file_name": "doc.pdf",
            "mime_type": "application/pdf",
            "purpose": "document",
        },
        headers=admin_headers,
    )
    file_path = upload_resp.json()["file_path"]

    confirm_resp = await client.post(
        "/api/storage/confirm",
        json={
            "file_path": file_path,
            "file_name": "doc.pdf",
            "mime_type": "application/pdf",
            "file_size": 10000,
            "entity_type": "resource",
            "entity_id": entity_id,
            "purpose": "document",
        },
        headers=admin_headers,
    )
    attachment_id = confirm_resp.json()["id"]

    resp = await client.get(
        f"/api/storage/attachments/{attachment_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == attachment_id
    assert resp.json()["download_url"] is not None


@pytest.mark.asyncio
async def test_delete_attachment(client: AsyncClient, admin_headers: dict):
    entity_id = str(uuid.uuid4())

    upload_resp = await client.post(
        "/api/storage/upload-url",
        json={
            "entity_type": "resource",
            "entity_id": entity_id,
            "file_name": "temp.jpg",
            "mime_type": "image/jpeg",
        },
        headers=admin_headers,
    )
    file_path = upload_resp.json()["file_path"]

    confirm_resp = await client.post(
        "/api/storage/confirm",
        json={
            "file_path": file_path,
            "file_name": "temp.jpg",
            "mime_type": "image/jpeg",
            "file_size": 500,
            "entity_type": "resource",
            "entity_id": entity_id,
        },
        headers=admin_headers,
    )
    attachment_id = confirm_resp.json()["id"]

    resp = await client.delete(
        f"/api/storage/attachments/{attachment_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 204

    resp = await client.get(
        f"/api/storage/attachments/{attachment_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_url_without_auth_fails(client: AsyncClient):
    resp = await client.post(
        "/api/storage/upload-url",
        json={
            "entity_type": "resource",
            "entity_id": str(uuid.uuid4()),
            "file_name": "test.jpg",
        },
    )
    assert resp.status_code in (400, 401, 403)
