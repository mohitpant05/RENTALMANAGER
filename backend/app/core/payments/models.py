import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TENANT_PAYMENT_TABLES: set[str] = {"payments"}


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", unique=True, index=True)
    amount: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=10)
    provider: str = Field(default="manual", max_length=20)
    status: str = Field(default="pending", max_length=30)
    provider_ref: str | None = Field(default=None, max_length=255)
    provider_data: dict | None = Field(default=None, sa_column=Column(JSONB))
    paid_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    refund_amount: float | None = Field(default=None)
    refunded_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
