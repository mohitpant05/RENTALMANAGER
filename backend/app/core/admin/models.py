import enum
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class DemoRequestStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


_demo_status_enum = sa.Enum(
    DemoRequestStatus,
    name="demorequeststatusenum",
    create_type=False,
)


class DemoRequest(SQLModel, table=True):
    __tablename__ = "demo_requests"
    __table_args__ = (
        UniqueConstraint("email", "slot_start", name="uq_demo_email_slot"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    email: str = Field(max_length=255, index=True)
    company: str | None = Field(default=None, max_length=255)
    message: str | None = Field(default=None, max_length=2000)
    slot_start: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    slot_end: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    status: DemoRequestStatus = Field(
        default=DemoRequestStatus.pending,
        sa_column=Column(_demo_status_enum, nullable=False, server_default="pending"),
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class TenantTheme(SQLModel, table=True):
    __tablename__ = "tenant_themes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", unique=True, index=True)
    brand: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    colors: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    typography: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    components: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    features: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
