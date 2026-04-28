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
