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
