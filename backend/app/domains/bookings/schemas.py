import uuid
from datetime import date, datetime

from pydantic import BaseModel, field_validator

from app.domains.bookings.state_machine import ALL_STATUSES


class AddonSchedule(BaseModel):
    date: date
    start_time: str | None = None
    end_time: str | None = None


class BookingCreate(BaseModel):
    resource_id: uuid.UUID
    hold_token: str
    hold_tokens: list[str] = []
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    auto_confirm: bool = True
    user_id: uuid.UUID | None = None
    schedules: list[AddonSchedule] | None = None


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
    service_fee: float
    platform_commission: float
    owner_payout: float
    customer_total: float
    hold_token: str | None
    cancellation_policy: dict | None
    notes: str | None
    schedules: list[dict] | None
    auto_confirm: bool
    parent_booking_id: uuid.UUID | None
    booking_group_id: uuid.UUID | None
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


class BookingItemCreate(BaseModel):
    resource_id: uuid.UUID
    hold_token: str
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    auto_confirm: bool = True
    schedules: list[AddonSchedule] | None = None


class BundledBookingCreate(BaseModel):
    primary: BookingItemCreate
    addons: list[BookingItemCreate] = []


class AddAddonRequest(BaseModel):
    resource_id: uuid.UUID
    hold_token: str
    hold_tokens: list[str] = []
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    auto_confirm: bool = True
    schedules: list[AddonSchedule] | None = None


class BookingGroupResponse(BaseModel):
    group_id: uuid.UUID
    primary: BookingResponse
    addons: list[BookingResponse]


class PagedBookingResponse(BaseModel):
    data: list[BookingResponse]
    total: int
