import uuid
from datetime import datetime

from pydantic import BaseModel


class PayoutCreate(BaseModel):
    owner_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    currency: str = "USD"
    notes: str | None = None


class PayoutItemResponse(BaseModel):
    id: uuid.UUID
    payout_id: uuid.UUID
    booking_id: uuid.UUID
    booking_total: float
    commission: float
    owner_amount: float

    model_config = {"from_attributes": True}


class PayoutResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    amount: float
    currency: str
    status: str
    period_start: datetime | None
    period_end: datetime | None
    settled_at: datetime | None
    settled_by: uuid.UUID | None
    provider_ref: str | None
    notes: str | None
    created_at: datetime
    items: list[PayoutItemResponse] = []

    model_config = {"from_attributes": True}


class OwnerBalance(BaseModel):
    owner_id: uuid.UUID
    owner_name: str
    owner_email: str
    pending_amount: float
    currency: str
    booking_count: int
    last_settled: datetime | None
