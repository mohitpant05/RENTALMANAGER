import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PaymentResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: float
    currency: str
    provider: str
    status: str
    provider_ref: str | None
    paid_at: datetime | None
    refund_amount: float | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MarkPaidRequest(BaseModel):
    notes: str | None = None


class RefundRequest(BaseModel):
    amount: float | None = Field(default=None, ge=0, le=1_000_000)
    reason: str | None = None
