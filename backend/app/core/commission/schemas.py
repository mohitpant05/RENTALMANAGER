import uuid

from pydantic import BaseModel, Field

MAX_COMMISSION_FIXED = 1_000_000


class CommissionConfig(BaseModel):
    owner_percent: float = Field(default=0.0, ge=0, le=100)
    owner_fixed: float = Field(default=0.0, ge=0, le=MAX_COMMISSION_FIXED)
    customer_percent: float = Field(default=0.0, ge=0, le=100)
    customer_fixed: float = Field(default=0.0, ge=0, le=MAX_COMMISSION_FIXED)
    currency: str = "USD"


class CommissionBreakdown(BaseModel):
    total_price: float
    service_fee: float
    platform_commission: float
    owner_payout: float
    customer_total: float


class CommissionConfigUpdate(BaseModel):
    owner_percent: float | None = Field(default=None, ge=0, le=100)
    owner_fixed: float | None = Field(default=None, ge=0, le=MAX_COMMISSION_FIXED)
    customer_percent: float | None = Field(default=None, ge=0, le=100)
    customer_fixed: float | None = Field(default=None, ge=0, le=MAX_COMMISSION_FIXED)
    currency: str | None = None


class CommissionConfigResponse(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    config: CommissionConfig | None
    inherited_from: str | None
