import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

TENANT_RESOURCE_TABLES: set[str] = {
    "resource_types",
    "resources",
    "resource_availability",
    "resource_assignments",
}


class ResourceType(SQLModel, table=True):
    __tablename__ = "resource_types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100, index=True)
    icon: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    availability_model: str = Field(max_length=20)
    pricing_model: str = Field(max_length=20)
    attribute_schema: list | None = Field(default=None, sa_column=Column(JSONB))
    slot_config: dict | None = Field(default=None, sa_column=Column(JSONB))
    pricing_config: dict | None = Field(default=None, sa_column=Column(JSONB))
    cancellation_defaults: dict | None = Field(default=None, sa_column=Column(JSONB))
    commission_config: dict | None = Field(default=None, sa_column=Column(JSONB))
    hold_config: dict | None = Field(default=None, sa_column=Column(JSONB))
    booking_mode: str = Field(default="both", max_length=20)
    operating_hours: dict | None = Field(default=None, sa_column=Column(JSONB))
    buffer_minutes: int = Field(default=0)
    staff_booking_auto_confirm: bool = Field(default=True)
    requires_verification: bool = Field(default=False)
    role: str = Field(default="standalone", max_length=20)
    discovery_radius_km: float | None = Field(default=None)
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Resource(SQLModel, table=True):
    __tablename__ = "resources"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type_id: uuid.UUID = Field(foreign_key="resource_types.id", index=True)
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    location_lat: float | None = Field(default=None)
    location_lng: float | None = Field(default=None)
    location_address: str | None = Field(default=None, max_length=500)
    attributes: dict | None = Field(default=None, sa_column=Column(JSONB))
    base_price: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=3)
    status: str = Field(default="draft", max_length=20)
    rating_avg: float = Field(default=0.0)
    rating_count: int = Field(default=0)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    commission_config: dict | None = Field(default=None, sa_column=Column(JSONB))
    suspension_reason: str | None = Field(default=None, max_length=50)
    support_contact_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    version: int = Field(default=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ResourceAvailability(SQLModel, table=True):
    __tablename__ = "resource_availability"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    end_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    status: str = Field(default="held", max_length=20)
    hold_token: str | None = Field(default=None, max_length=100, index=True)
    hold_expires: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    booking_id: uuid.UUID | None = Field(default=None)
    version: int = Field(default=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ResourceAssignment(SQLModel, table=True):
    __tablename__ = "resource_assignments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    primary_resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    addon_resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    priority: int = Field(default=0)
    assigned_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
