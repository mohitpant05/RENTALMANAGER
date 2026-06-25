import uuid
from datetime import datetime

from pydantic import BaseModel


class ThemeUpdate(BaseModel):
    brand: dict | None = None
    colors: dict | None = None
    typography: dict | None = None
    components: dict | None = None
    features: dict | None = None


class ThemeResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    brand: dict
    colors: dict
    typography: dict
    components: dict
    features: dict
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantConfigUpdate(BaseModel):
    name: str | None = None
    base_currency: str | None = None
    timezone: str | None = None
    config: dict | None = None


SENSITIVE_CONFIG_KEYS = {
    "stripe_secret_key",
    "stripe_publishable_key",
    "razorpay_key_id",
    "razorpay_key_secret",
    "webhook_secret_stripe",
    "webhook_secret_razorpay",
    "smtp_password",
    "mandrill_api_key",
}


class TestEmailRequest(BaseModel):
    to: str


def _mask_config(config: dict | None) -> dict | None:
    if config is None:
        return None
    masked = {}
    for k, v in config.items():
        if k in SENSITIVE_CONFIG_KEYS and isinstance(v, str) and len(v) > 4:
            masked[k] = "••••" + v[-4:]
        else:
            masked[k] = v
    return masked


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    schema_name: str
    is_active: bool
    config: dict | None
    base_currency: str
    timezone: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_tenant(cls, tenant: object) -> "TenantResponse":
        resp = cls.model_validate(tenant)
        resp.config = _mask_config(resp.config)
        return resp


class DomainCreate(BaseModel):
    domain: str
    is_primary: bool = False


class DomainResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    domain: str
    is_primary: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StaffUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    user_type: str
    created_at: datetime
    roles: list[str] = []

    model_config = {"from_attributes": True}


class StaffInviteResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    user_type: str
    created_at: datetime
    roles: list[str] = []
    email_status: str = "queued"
    email_warning: str | None = None

    model_config = {"from_attributes": True}


class StaffInvite(BaseModel):
    email: str
    full_name: str
    user_type: str = "staff"
    role_slugs: list[str] = []


class ListerInvite(BaseModel):
    email: str
    full_name: str
    role_slugs: list[str] = ["lister"]
    manager_id: uuid.UUID | None = None


class ListerResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    user_type: str
    manager_id: uuid.UUID | None
    created_at: datetime
    roles: list[str] = []
    email_status: str = "queued"
    email_warning: str | None = None

    model_config = {"from_attributes": True}


class PlatformLoginRequest(BaseModel):
    email: str
    password: str


class PlatformTokenResponse(BaseModel):
    access_token: str


class DeactivationImpactResponse(BaseModel):
    resources_count: int
    pending_bookings_count: int


class TenantCreate(BaseModel):
    name: str
    slug: str
    base_currency: str = "USD"
    timezone: str = "UTC"


class DashboardStatsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    inactive_tenants: int
    total_users: int
    total_bookings: int
    services: dict


class PlatformSettingResponse(BaseModel):
    id: uuid.UUID
    key: str
    value: str
    description: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformSettingUpdate(BaseModel):
    value: str
    description: str | None = None


class ValidateKeyRequest(BaseModel):
    key: str


class CustomerCreate(BaseModel):
    email: str
    full_name: str
    phone: str | None = None


class CustomerResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    user_type: str
    created_at: datetime
    booking_count: int = 0

    model_config = {"from_attributes": True}
