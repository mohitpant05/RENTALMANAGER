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
