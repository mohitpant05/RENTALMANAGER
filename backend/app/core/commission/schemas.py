import uuid

from pydantic import BaseModel


class CommissionConfig(BaseModel):
    owner_percent: float = 0.0
    owner_fixed: float = 0.0
    customer_percent: float = 0.0
    customer_fixed: float = 0.0
    currency: str = "USD"


class CommissionBreakdown(BaseModel):
    total_price: float
    service_fee: float
    platform_commission: float
    owner_payout: float
    customer_total: float


class CommissionConfigUpdate(BaseModel):
    owner_percent: float | None = None
    owner_fixed: float | None = None
    customer_percent: float | None = None
    customer_fixed: float | None = None
    currency: str | None = None


class CommissionConfigResponse(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    config: CommissionConfig | None
    inherited_from: str | None
