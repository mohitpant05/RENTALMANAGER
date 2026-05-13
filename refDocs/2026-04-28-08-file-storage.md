# File Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a file storage service using MinIO for resource images, user avatars, and general file uploads with per-tenant bucket isolation, presigned upload/download URLs, and image metadata tracking.

**Architecture:** A storage service module (`app/core/storage/`) wraps the MinIO Python SDK. Each tenant gets a bucket (`tenant-{slug}`). Files are organized by purpose (`resources/{id}/`, `avatars/{id}/`). Upload flow: client requests presigned URL → uploads directly to MinIO → confirms via API → metadata saved to DB. Download uses presigned URLs for time-limited access. An `Attachment` model tracks file metadata (path, mime type, size, linked entity).

**Tech Stack:** MinIO Python SDK (7.2.20), FastAPI, SQLModel

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/core/storage/__init__.py` | Package marker |
| `backend/app/core/storage/client.py` | MinIO client singleton + bucket management |
| `backend/app/core/storage/service.py` | Upload, download URLs, delete, list files |
| `backend/app/core/storage/models.py` | Attachment model + TENANT_STORAGE_TABLES |
| `backend/app/core/storage/schemas.py` | Request/response schemas |
| `backend/app/core/storage/router.py` | API endpoints |
| `backend/app/core/tenancy/provisioning.py` | Modified: register storage tables + create bucket |
| `backend/app/main.py` | Modified: register storage router |
| `backend/tests/test_storage_unit.py` | Unit tests |
| `backend/tests/test_storage_integration.py` | Integration tests |

---

### Task 1: MinIO client and bucket management

**Files:**
- Create: `backend/app/core/storage/__init__.py`
- Create: `backend/app/core/storage/client.py`

- [ ] **Step 1: Create package**

```python
# backend/app/core/storage/__init__.py
```

Empty file.

- [ ] **Step 2: Create client module**

```python
# backend/app/core/storage/client.py
from minio import Minio

from app.config import get_settings


def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,
    )


def get_tenant_bucket(tenant_slug: str) -> str:
    safe = tenant_slug.replace("_", "-").lower()
    return f"tenant-{safe}"


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
```

- [ ] **Step 3: Verify**

Run: `docker exec rm-backend python -c "from app.core.storage.client import get_minio_client, get_tenant_bucket, ensure_bucket; c = get_minio_client(); b = get_tenant_bucket('test-tenant'); ensure_bucket(c, b); print('Bucket:', b, 'exists:', c.bucket_exists(b))"`

Expected: `Bucket: tenant-test-tenant exists: True`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/storage/
git commit -m "feat(storage): add MinIO client singleton and bucket management"
```

---

### Task 2: Attachment model and table registration

**Files:**
- Create: `backend/app/core/storage/models.py`
- Modify: `backend/app/core/tenancy/provisioning.py`

- [ ] **Step 1: Create Attachment model**

```python
# backend/app/core/storage/models.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

TENANT_STORAGE_TABLES: set[str] = {"attachments"}


class Attachment(SQLModel, table=True):
    __tablename__ = "attachments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    entity_type: str = Field(max_length=50, index=True)
    entity_id: uuid.UUID = Field(index=True)
    file_path: str = Field(max_length=500)
    file_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    file_size: int = Field(default=0)
    purpose: str = Field(default="image", max_length=50)
    uploaded_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
```

`entity_type` is `"resource"`, `"user"`, `"review"`, etc.
`entity_id` is the UUID of the linked entity.
`purpose` is `"image"`, `"avatar"`, `"document"`, `"verification"`.

- [ ] **Step 2: Register in provisioning**

In `backend/app/core/tenancy/provisioning.py`, add:

```python
from app.core.storage.models import TENANT_STORAGE_TABLES  # noqa: F401
```

And:

```python
TENANT_TABLE_REGISTRY.update(TENANT_STORAGE_TABLES)
```

- [ ] **Step 3: Verify**

Run: `docker exec rm-backend python -c "from app.core.storage.models import Attachment, TENANT_STORAGE_TABLES; from app.core.tenancy.provisioning import TENANT_TABLE_REGISTRY; assert 'attachments' in TENANT_TABLE_REGISTRY; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/storage/models.py backend/app/core/tenancy/provisioning.py
git commit -m "feat(storage): add Attachment model and register tenant table"
```

---

### Task 3: Storage service

**Files:**
- Create: `backend/app/core/storage/service.py`

- [ ] **Step 1: Create service**

```python
# backend/app/core/storage/service.py
import uuid
from datetime import timedelta

from fastapi import HTTPException
from minio import Minio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.storage.client import ensure_bucket, get_minio_client, get_tenant_bucket
from app.core.storage.models import Attachment


def generate_upload_url(
    tenant_slug: str,
    entity_type: str,
    entity_id: str,
    file_name: str,
    mime_type: str = "application/octet-stream",
    expires_minutes: int = 15,
) -> dict:
    client = get_minio_client()
    bucket = get_tenant_bucket(tenant_slug)
    ensure_bucket(client, bucket)

    file_path = f"{entity_type}/{entity_id}/{uuid.uuid4().hex}_{file_name}"
    url = client.presigned_put_object(
        bucket, file_path, expires=timedelta(minutes=expires_minutes)
    )
    return {
        "upload_url": url,
        "file_path": file_path,
        "bucket": bucket,
    }


def generate_download_url(
    tenant_slug: str,
    file_path: str,
    expires_minutes: int = 60,
) -> str:
    client = get_minio_client()
    bucket = get_tenant_bucket(tenant_slug)
    return client.presigned_get_object(
        bucket, file_path, expires=timedelta(minutes=expires_minutes)
    )


def delete_file(tenant_slug: str, file_path: str) -> None:
    client = get_minio_client()
    bucket = get_tenant_bucket(tenant_slug)
    client.remove_object(bucket, file_path)


async def create_attachment(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    file_path: str,
    file_name: str,
    mime_type: str,
    file_size: int,
    purpose: str,
    uploaded_by: uuid.UUID,
) -> Attachment:
    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        file_path=file_path,
        file_name=file_name,
        mime_type=mime_type,
        file_size=file_size,
        purpose=purpose,
        uploaded_by=uploaded_by,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    return attachment


async def list_attachments(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
) -> list[Attachment]:
    result = await session.exec(
        select(Attachment).where(
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        ).order_by(Attachment.created_at.desc())
    )
    return list(result.all())


async def get_attachment(
    session: AsyncSession, attachment_id: uuid.UUID
) -> Attachment:
    result = await session.exec(
        select(Attachment).where(Attachment.id == attachment_id)
    )
    attachment = result.first()
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return attachment


async def delete_attachment(
    session: AsyncSession,
    attachment_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_slug: str,
    is_admin: bool = False,
) -> None:
    attachment = await get_attachment(session, attachment_id)
    if not is_admin and attachment.uploaded_by != user_id:
        raise HTTPException(status_code=403, detail="Not the file owner")

    delete_file(tenant_slug, attachment.file_path)
    await session.delete(attachment)
    await session.commit()
```

- [ ] **Step 2: Verify**

Run: `docker exec rm-backend python -c "from app.core.storage.service import generate_upload_url, generate_download_url, create_attachment; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/storage/service.py
git commit -m "feat(storage): add storage service with presigned URLs and attachment CRUD"
```

---

### Task 4: Schemas and router

**Files:**
- Create: `backend/app/core/storage/schemas.py`
- Create: `backend/app/core/storage/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create schemas**

```python
# backend/app/core/storage/schemas.py
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class UploadRequest(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    file_name: str
    mime_type: str = "application/octet-stream"
    purpose: str = "image"

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        allowed = {"resource", "user", "review", "verification"}
        if v not in allowed:
            raise ValueError(f"entity_type must be one of {allowed}")
        return v

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        allowed = {"image", "avatar", "document", "verification"}
        if v not in allowed:
            raise ValueError(f"purpose must be one of {allowed}")
        return v


class UploadResponse(BaseModel):
    upload_url: str
    file_path: str
    bucket: str


class ConfirmUploadRequest(BaseModel):
    file_path: str
    file_name: str
    mime_type: str
    file_size: int
    entity_type: str
    entity_id: uuid.UUID
    purpose: str = "image"


class AttachmentResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    file_path: str
    file_name: str
    mime_type: str
    file_size: int
    purpose: str
    uploaded_by: uuid.UUID
    download_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Create router**

```python
# backend/app/core/storage/router.py
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.auth.models import User
from app.core.storage.schemas import (
    AttachmentResponse,
    ConfirmUploadRequest,
    UploadRequest,
    UploadResponse,
)
from app.core.storage.service import (
    create_attachment,
    delete_attachment,
    generate_download_url,
    generate_upload_url,
    get_attachment,
    list_attachments,
)
from app.core.tenancy.context import get_current_tenant
from app.database import get_db
from fastapi import HTTPException

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.post("/upload-url", response_model=UploadResponse)
async def request_upload_url(
    data: UploadRequest,
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    result = generate_upload_url(
        tenant_ctx.tenant.slug,
        data.entity_type,
        str(data.entity_id),
        data.file_name,
        data.mime_type,
    )
    return UploadResponse(**result)


@router.post("/confirm", response_model=AttachmentResponse, status_code=201)
async def confirm_upload(
    data: ConfirmUploadRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    attachment = await create_attachment(
        session,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        file_path=data.file_path,
        file_name=data.file_name,
        mime_type=data.mime_type,
        file_size=data.file_size,
        purpose=data.purpose,
        uploaded_by=user.id,
    )
    url = generate_download_url(tenant_ctx.tenant.slug, attachment.file_path)
    resp = AttachmentResponse.model_validate(attachment)
    resp.download_url = url
    return resp


@router.get("/attachments", response_model=list[AttachmentResponse])
async def list_entity_attachments(
    entity_type: str = Query(...),
    entity_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    attachments = await list_attachments(session, entity_type, entity_id)
    results = []
    for a in attachments:
        resp = AttachmentResponse.model_validate(a)
        resp.download_url = generate_download_url(
            tenant_ctx.tenant.slug, a.file_path
        )
        results.append(resp)
    return results


@router.get("/attachments/{attachment_id}", response_model=AttachmentResponse)
async def get_one_attachment(
    attachment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    attachment = await get_attachment(session, attachment_id)
    resp = AttachmentResponse.model_validate(attachment)
    resp.download_url = generate_download_url(
        tenant_ctx.tenant.slug, attachment.file_path
    )
    return resp


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_one_attachment(
    attachment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    is_admin = user.user_type == "admin"
    await delete_attachment(
        session, attachment_id, user.id, tenant_ctx.tenant.slug, is_admin=is_admin
    )
```

- [ ] **Step 3: Register router in main.py**

Add import:

```python
from app.core.storage.router import router as storage_router
```

And:

```python
app.include_router(storage_router)
```

- [ ] **Step 4: Verify**

Run: `docker exec rm-backend python -c "from app.main import app; paths = [r.path for r in app.routes if hasattr(r, 'path')]; assert '/api/storage/upload-url' in paths; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/storage/schemas.py backend/app/core/storage/router.py backend/app/main.py
git commit -m "feat(storage): add file storage API with presigned upload/download"
```

---

### Task 5: Unit tests

**Files:**
- Create: `backend/tests/test_storage_unit.py`

- [ ] **Step 1: Write unit tests**

```python
# backend/tests/test_storage_unit.py
import uuid
from datetime import UTC, datetime

from pydantic import ValidationError

from app.core.storage.client import get_tenant_bucket
from app.core.storage.models import TENANT_STORAGE_TABLES, Attachment
from app.core.storage.schemas import (
    AttachmentResponse,
    ConfirmUploadRequest,
    UploadRequest,
)


def test_get_tenant_bucket():
    assert get_tenant_bucket("test-tenant") == "tenant-test-tenant"
    assert get_tenant_bucket("my_tenant") == "tenant-my-tenant"


def test_attachment_model_defaults():
    a = Attachment(
        entity_type="resource",
        entity_id=uuid.uuid4(),
        file_path="resources/abc/img.jpg",
        file_name="img.jpg",
        mime_type="image/jpeg",
        file_size=1024,
        purpose="image",
        uploaded_by=uuid.uuid4(),
    )
    assert a.file_size == 1024
    assert a.purpose == "image"


def test_tenant_storage_tables():
    assert TENANT_STORAGE_TABLES == {"attachments"}


def test_upload_request_valid():
    r = UploadRequest(
        entity_type="resource",
        entity_id=uuid.uuid4(),
        file_name="photo.jpg",
        mime_type="image/jpeg",
    )
    assert r.purpose == "image"


def test_upload_request_invalid_entity_type():
    try:
        UploadRequest(
            entity_type="invalid",
            entity_id=uuid.uuid4(),
            file_name="photo.jpg",
        )
        assert False, "Should raise"
    except ValidationError:
        pass


def test_upload_request_invalid_purpose():
    try:
        UploadRequest(
            entity_type="resource",
            entity_id=uuid.uuid4(),
            file_name="photo.jpg",
            purpose="invalid",
        )
        assert False, "Should raise"
    except ValidationError:
        pass


def test_confirm_upload_request():
    r = ConfirmUploadRequest(
        file_path="resources/abc/img.jpg",
        file_name="img.jpg",
        mime_type="image/jpeg",
        file_size=2048,
        entity_type="resource",
        entity_id=uuid.uuid4(),
    )
    assert r.file_size == 2048
    assert r.purpose == "image"


def test_attachment_response_from_model():
    a = Attachment(
        id=uuid.uuid4(),
        entity_type="resource",
        entity_id=uuid.uuid4(),
        file_path="resources/abc/img.jpg",
        file_name="img.jpg",
        mime_type="image/jpeg",
        file_size=1024,
        purpose="image",
        uploaded_by=uuid.uuid4(),
        created_at=datetime.now(UTC),
    )
    resp = AttachmentResponse.model_validate(a)
    assert resp.file_name == "img.jpg"
    assert resp.download_url is None
```

- [ ] **Step 2: Run tests**

Run: `docker exec rm-backend python -m pytest tests/test_storage_unit.py -v`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_storage_unit.py
git commit -m "test(storage): add unit tests for client, model, schemas"
```

---

### Task 6: Integration tests

**Files:**
- Create: `backend/tests/test_storage_integration.py`

- [ ] **Step 1: Write integration tests**

```python
# backend/tests/test_storage_integration.py
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
async def test_upload_url_without_tenant_fails(client: AsyncClient):
    resp = await client.post(
        "/api/storage/upload-url",
        json={
            "entity_type": "resource",
            "entity_id": str(uuid.uuid4()),
            "file_name": "test.jpg",
        },
    )
    assert resp.status_code in (400, 401)
```

- [ ] **Step 2: Run tests**

Run: `docker exec rm-backend python -m pytest tests/test_storage_integration.py -v --tb=short`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_storage_integration.py
git commit -m "test(storage): add integration tests for upload, confirm, list, delete"
```

---

### Task 7: Final verification + cleanup

- [ ] **Step 1: Run full test suite**

Run: `docker exec rm-backend python -m pytest --tb=short -q`

Expected: All pass (204 existing + new storage tests).

- [ ] **Step 2: Lint check and fix**

Run: `docker exec rm-backend python -m ruff check --fix app/core/storage/ tests/test_storage_unit.py tests/test_storage_integration.py app/main.py app/core/tenancy/provisioning.py`

- [ ] **Step 3: Commit if needed**

```bash
git add -A && git commit -m "style: fix lint issues in storage module" --allow-empty
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| MinIO for images, documents, verification files | Task 1 (client), Task 3 (service) |
| Per-tenant bucket isolation | Task 1 (get_tenant_bucket) |
| Presigned upload URLs | Task 3 (generate_upload_url) |
| Presigned download URLs | Task 3 (generate_download_url) |
| File metadata tracking | Task 2 (Attachment model) |
| File delete with ownership check | Task 3 (delete_attachment) |
| S3-compatible (MinIO → AWS S3 migration) | Built-in — MinIO SDK is S3-compatible |
