import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

VALID_AVAILABILITY_MODELS = {"date_range", "time_slot", "hourly"}
VALID_PRICING_MODELS = {"fixed_per_day", "fixed_per_slot", "per_hour", "tiered"}
VALID_RESOURCE_STATUSES = {"draft", "active", "inactive", "archived"}


class ResourceTypeCreate(BaseModel):
    name: str
    slug: str
    icon: str | None = None
    description: str | None = None
    availability_model: str
    pricing_model: str
    attribute_schema: list[dict] | None = None
    slot_config: dict | None = None
    pricing_config: dict | None = None
    cancellation_defaults: dict | None = None
    requires_verification: bool = False

    @field_validator("availability_model")
    @classmethod
    def check_availability_model(cls, v: str) -> str:
        if v not in VALID_AVAILABILITY_MODELS:
            raise ValueError(f"Must be one of {VALID_AVAILABILITY_MODELS}")
        return v

    @field_validator("pricing_model")
    @classmethod
    def check_pricing_model(cls, v: str) -> str:
        if v not in VALID_PRICING_MODELS:
            raise ValueError(f"Must be one of {VALID_PRICING_MODELS}")
        return v


class ResourceTypeUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    icon: str | None = None
    description: str | None = None
    attribute_schema: list[dict] | None = None
    slot_config: dict | None = None
    pricing_config: dict | None = None
    cancellation_defaults: dict | None = None
    requires_verification: bool | None = None
    is_active: bool | None = None


class ResourceTypeResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    icon: str | None
    description: str | None
    availability_model: str
    pricing_model: str
    attribute_schema: list[dict] | None
    slot_config: dict | None
    pricing_config: dict | None
    cancellation_defaults: dict | None
    requires_verification: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResourceCreate(BaseModel):
    type_id: uuid.UUID
    name: str
    description: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    location_address: str | None = None
    attributes: dict | None = None
    base_price: float
    currency: str = "USD"

    @field_validator("base_price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v


class ResourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    location_address: str | None = None
    attributes: dict | None = None
    base_price: float | None = None
    currency: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_RESOURCE_STATUSES:
            raise ValueError(f"Must be one of {VALID_RESOURCE_STATUSES}")
        return v

    @field_validator("base_price")
    @classmethod
    def price_positive(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Price must be non-negative")
        return v


class ResourceResponse(BaseModel):
    id: uuid.UUID
    type_id: uuid.UUID
    name: str
    description: str | None
    location_lat: float | None
    location_lng: float | None
    location_address: str | None
    attributes: dict | None
    base_price: float
    currency: str
    status: str
    rating_avg: float
    rating_count: int
    owner_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class AvailabilityCheckRequest(BaseModel):
    start: datetime
    end: datetime


class AvailabilityCheckResponse(BaseModel):
    available: bool
    price: float | None = None


class HoldRequest(BaseModel):
    start: datetime
    end: datetime
    hold_minutes: int = 10


class HoldResponse(BaseModel):
    hold_token: str
    expires: datetime
    price: float


class ReleaseRequest(BaseModel):
    hold_token: str


class PriceCalculateRequest(BaseModel):
    start: datetime
    end: datetime
