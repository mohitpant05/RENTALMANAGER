import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TENANT_REVIEW_TABLES: set[str] = {"reviews"}


class Review(SQLModel, table=True):
    __tablename__ = "reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", index=True)
    resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    reviewer_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    target_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", index=True
    )
    direction: str = Field(max_length=20, index=True)
    rating: int = Field(ge=1, le=5)
    category_ratings: dict | None = Field(default=None, sa_column=Column(JSONB))
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    status: str = Field(default="published", max_length=20, index=True)
    moderation_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
