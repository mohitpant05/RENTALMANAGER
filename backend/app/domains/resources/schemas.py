import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

MAX_PRICE = 1_000_000
MAX_RADIUS_KM = 50_000
MAX_DISPLAY_ORDER = 1_000_000
MAX_PRIORITY = 1_000_000

VALID_AVAILABILITY_MODELS = {"date_range", "time_slot", "hourly"}
VALID_PRICING_MODELS = {"fixed_per_day", "fixed_per_slot", "per_hour", "tiered"}
VALID_RESOURCE_STATUSES = {"draft", "active", "inactive", "archived"}
VALID_RESOURCE_TYPE_ROLES = {"primary", "addon", "standalone", "hidden"}
VALID_HOLD_UNITS = {"seconds", "minutes"}
VALID_BOOKING_MODES = {"individual", "bundled", "both"}


class OperatingHours(BaseModel):
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def check_time_format(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Must be HH:MM format")
        h, m = int(v[:2]), int(v[3:])
        if h > 23 or m > 59:
            raise ValueError("Invalid time")
        return v


class HoldConfig(BaseModel):
    unit: str
    value: int = Field(ge=1)

    @field_validator("unit")
    @classmethod
    def check_unit(cls, v: str) -> str:
        if v not in VALID_HOLD_UNITS:
            raise ValueError(f"unit must be one of {VALID_HOLD_UNITS}")
        return v

    @field_validator("value")
    @classmethod
    def check_value(cls, v: int, info) -> int:
        unit = info.data.get("unit", "minutes")
        if unit == "minutes" and v > 60:
            raise ValueError("Hold duration cannot exceed 60 minutes")
        if unit == "seconds" and v > 3600:
            raise ValueError("Hold duration cannot exceed 3600 seconds")
        return v

    def to_minutes(self) -> int:
        if self.unit == "seconds":
            return max(1, self.value // 60)
        return self.value

    def to_seconds(self) -> int:
        if self.unit == "minutes":
            return self.value * 60
        return self.value


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
    role: str = "standalone"
    discovery_radius_km: float | None = Field(default=None, ge=0, le=MAX_RADIUS_KM)
    display_order: int = Field(default=0, ge=0, le=MAX_DISPLAY_ORDER)
    hold_config: HoldConfig | None = None
    booking_mode: str = "both"
    operating_hours: OperatingHours | None = None
    buffer_minutes: int = Field(default=0, ge=0, le=120)

    @field_validator("role")
    @classmethod
    def check_role(cls, v: str) -> str:
        if v not in VALID_RESOURCE_TYPE_ROLES:
            raise ValueError(f"Must be one of {VALID_RESOURCE_TYPE_ROLES}")
        return v

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

    @field_validator("booking_mode")
    @classmethod
    def check_booking_mode(cls, v: str) -> str:
        if v not in VALID_BOOKING_MODES:
            raise ValueError(f"Must be one of {VALID_BOOKING_MODES}")
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
    role: str | None = None
    discovery_radius_km: float | None = Field(default=None, ge=0, le=MAX_RADIUS_KM)
    display_order: int | None = Field(default=None, ge=0, le=MAX_DISPLAY_ORDER)
    availability_model: str | None = None
    pricing_model: str | None = None
    hold_config: HoldConfig | None = None
    booking_mode: str | None = None
    operating_hours: OperatingHours | None = None
    buffer_minutes: int | None = Field(default=None, ge=0, le=120)
    is_active: bool | None = None

    @field_validator("availability_model")
    @classmethod
    def check_avail_model_update(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_AVAILABILITY_MODELS:
            raise ValueError(f"Must be one of {VALID_AVAILABILITY_MODELS}")
        return v

    @field_validator("pricing_model")
    @classmethod
    def check_pricing_model_update(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_PRICING_MODELS:
            raise ValueError(f"Must be one of {VALID_PRICING_MODELS}")
        return v

    @field_validator("booking_mode")
    @classmethod
    def check_booking_mode(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_BOOKING_MODES:
            raise ValueError(f"Must be one of {VALID_BOOKING_MODES}")
        return v


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
    role: str
    discovery_radius_km: float | None
    display_order: int
    hold_config: dict | None
    booking_mode: str
    operating_hours: dict | None
    buffer_minutes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResourceCreate(BaseModel):
    type_id: uuid.UUID
    name: str
    description: str | None = None
    location_lat: float | None = Field(default=None, ge=-90, le=90)
    location_lng: float | None = Field(default=None, ge=-180, le=180)
    location_address: str | None = None
    attributes: dict | None = None
    base_price: float = Field(ge=0, le=MAX_PRICE)
    currency: str | None = None
    support_contact_id: uuid.UUID | None = None
    slot_config: dict | None = None


class ResourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location_lat: float | None = Field(default=None, ge=-90, le=90)
    location_lng: float | None = Field(default=None, ge=-180, le=180)
    location_address: str | None = None
    attributes: dict | None = None
    base_price: float | None = Field(default=None, ge=0, le=MAX_PRICE)
    currency: str | None = None
    status: str | None = None
    support_contact_id: uuid.UUID | None = None
    slot_config: dict | None = None

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_RESOURCE_STATUSES:
            raise ValueError(f"Must be one of {VALID_RESOURCE_STATUSES}")
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
    slot_config: dict | None
    support_contact_id: uuid.UUID | None
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
    hold_minutes: int = Field(default=10, ge=1, le=60)


class HoldResponse(BaseModel):
    hold_token: str
    expires: datetime
    price: float


class ReleaseRequest(BaseModel):
    hold_token: str


class ScheduleCheckItem(BaseModel):
    date: date
    start_time: str | None = None
    end_time: str | None = None


class SchedulesCheckRequest(BaseModel):
    schedules: list[ScheduleCheckItem]
    availability_model: str


class ScheduleState(BaseModel):
    date: date
    start_time: str | None = None
    end_time: str | None = None
    available: bool


class SchedulesCheckResponse(BaseModel):
    available: bool
    schedule_states: list[ScheduleState]


class AvailabilitySlotResponse(BaseModel):
    id: uuid.UUID
    resource_id: uuid.UUID
    resource_name: str
    resource_type_name: str
    start_time: datetime
    end_time: datetime
    status: str
    hold_token: str | None = None
    hold_expires: datetime | None = None
    booking_id: uuid.UUID | None = None
    customer_name: str | None = None

    model_config = {"from_attributes": True, "arbitrary_types_allowed": True}


class PriceCalculateRequest(BaseModel):
    start: datetime
    end: datetime


class ResourceAssignmentCreate(BaseModel):
    addon_resource_id: uuid.UUID
    priority: int = Field(default=0, ge=0, le=MAX_PRIORITY)


class ResourceAssignmentUpdate(BaseModel):
    priority: int = Field(ge=0, le=MAX_PRIORITY)


class ResourceAssignmentResponse(BaseModel):
    id: uuid.UUID
    primary_resource_id: uuid.UUID
    addon_resource_id: uuid.UUID
    priority: int
    assigned_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
