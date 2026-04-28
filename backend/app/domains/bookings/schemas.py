import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.domains.bookings.state_machine import ALL_STATUSES


class BookingCreate(BaseModel):
    resource_id: uuid.UUID
    hold_token: str
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    auto_confirm: bool = True


class BookingCancel(BaseModel):
    reason: str | None = None


class BookingReject(BaseModel):
    reason: str | None = None


class BookingResponse(BaseModel):
    id: uuid.UUID
    resource_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    start_time: datetime
    end_time: datetime
    total_price: float
    currency: str
    hold_token: str | None
    cancellation_policy: dict | None
    notes: str | None
    auto_confirm: bool
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    refund_percent: float | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingListParams(BaseModel):
    status: str | None = None
    resource_id: uuid.UUID | None = None
    offset: int = 0
    limit: int = 50

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ALL_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {sorted(ALL_STATUSES)}")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("Limit must be between 1 and 100")
        return v
