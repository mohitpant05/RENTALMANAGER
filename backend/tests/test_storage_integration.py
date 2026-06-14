import uuid

import pytest
from httpx import AsyncClient


def _upload_payload(entity_id: str, filename: str = "test.jpg", mime: str = "image/jpeg"):
    return {
        "file": (filename, b"fake-image-bytes", mime),
        "entity_type": ("", "resource"),
        "entity_id": ("", entity_id),
    }


@pytest.mark.asyncio
async def test_upload_file(client: AsyncClient, admin_headers: dict):
    entity_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/storage/upload",
        files=_upload_payload(entity_id),
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"] == "test.jpg"
    assert data["mime_type"] == "image/jpeg"
    assert data["file_size"] == 15
    assert data["entity_type"] == "resource"
    assert data["entity_id"] == entity_id
    assert data["download_url"] is not None


@pytest.mark.asyncio
async def test_upload_and_list(client: AsyncClient, admin_headers: dict):
    entity_id = str(uuid.uuid4())

    upload_resp = await client.post(
        "/api/storage/upload",
        files=_upload_payload(entity_id, "villa.jpg"),
        headers=admin_headers,
    )
    assert upload_resp.status_code == 201

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
        "/api/storage/upload",
        files=_upload_payload(entity_id, "doc.pdf", "application/pdf"),
        headers=admin_headers | {"Content-Type": None},
    )
    assert upload_resp.status_code == 201
    attachment_id = upload_resp.json()["id"]

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
        "/api/storage/upload",
        files=_upload_payload(entity_id),
        headers=admin_headers,
    )
    assert upload_resp.status_code == 201
    attachment_id = upload_resp.json()["id"]

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
async def test_list_attachments_without_auth(client: AsyncClient, admin_headers: dict):
    entity_id = str(uuid.uuid4())

    await client.post(
        "/api/storage/upload",
        files=_upload_payload(entity_id, "public.jpg"),
        headers=admin_headers,
    )

    resp = await client.get(
        f"/api/storage/attachments?entity_type=resource&entity_id={entity_id}",
    )
    assert resp.status_code == 200
    attachments = resp.json()
    assert len(attachments) >= 1
    assert attachments[0]["file_name"] == "public.jpg"


@pytest.mark.asyncio
async def test_upload_without_auth_fails(client: AsyncClient):
    entity_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/storage/upload",
        files=_upload_payload(entity_id),
    )
    assert resp.status_code in (400, 401, 403)


@pytest.mark.asyncio
async def test_unsupported_file_type_rejected(client: AsyncClient, admin_headers: dict):
    entity_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/storage/upload",
        files=_upload_payload(entity_id, "malware.exe", "application/x-msdownload"),
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "unsupported" in resp.json()["detail"].lower()
