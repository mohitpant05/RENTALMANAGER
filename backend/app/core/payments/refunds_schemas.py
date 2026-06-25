import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RefundPendingItem(BaseModel):
    booking_id: uuid.UUID
    payment_id: uuid.UUID
    customer_name: str
    customer_email: str
    resource_name: str
    cancelled_at: datetime | None
    start_time: datetime
    booking_amount: float
    currency: str
    refund_percent: float
    refund_amount: float
    payment_status: str
    provider: str

    model_config = {"from_attributes": True}


class RefundSettleRequest(BaseModel):
    payment_id: uuid.UUID
    override_percent: float | None = Field(default=None, ge=0, le=100)


class BulkRefundSettleRequest(BaseModel):
    items: list[RefundSettleRequest] = Field(min_length=1)


class RefundSettleResult(BaseModel):
    payment_id: uuid.UUID
    success: bool
    refund_amount: float | None = None
    error: str | None = None


class BulkRefundSettleResponse(BaseModel):
    results: list[RefundSettleResult]
    settled_count: int
    failed_count: int
