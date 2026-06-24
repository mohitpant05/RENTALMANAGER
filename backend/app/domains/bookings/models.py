import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TENANT_BOOKING_TABLES: set[str] = {"bookings"}


class Booking(SQLModel, table=True):
    __tablename__ = "bookings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", max_length=20, index=True)
    start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    end_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    total_price: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=10)
    service_fee: float = Field(default=0.0)
    platform_commission: float = Field(default=0.0)
    owner_payout: float = Field(default=0.0)
    customer_total: float = Field(default=0.0)
    hold_token: str | None = Field(default=None, max_length=100)
    cancellation_policy: dict | None = Field(default=None, sa_column=Column(JSONB))
    notes: str | None = Field(default=None, max_length=1000)
    schedules: list[dict] | None = Field(default=None, sa_column=Column(JSONB))
    auto_confirm: bool = Field(default=True)
    parent_booking_id: uuid.UUID | None = Field(default=None, foreign_key="bookings.id", index=True)
    booking_group_id: uuid.UUID | None = Field(default=None, index=True)
    confirmed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    cancelled_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    cancellation_reason: str | None = Field(default=None, max_length=500)
    refund_percent: float | None = Field(default=None)
    timezone: str = Field(default="UTC", max_length=50)
    version: int = Field(default=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
