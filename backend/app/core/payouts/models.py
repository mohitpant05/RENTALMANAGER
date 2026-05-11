import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel

TENANT_PAYOUT_TABLES: set[str] = {"payouts", "payout_items"}


class Payout(SQLModel, table=True):
    __tablename__ = "payouts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    amount: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=10)
    status: str = Field(default="pending", max_length=20)
    period_start: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    period_end: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    settled_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    settled_by: uuid.UUID | None = Field(default=None)
    provider_ref: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PayoutItem(SQLModel, table=True):
    __tablename__ = "payout_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    payout_id: uuid.UUID = Field(foreign_key="payouts.id", index=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", index=True)
    booking_total: float = Field(default=0.0)
    commission: float = Field(default=0.0)
    owner_amount: float = Field(default=0.0)
