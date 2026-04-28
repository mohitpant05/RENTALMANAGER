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


class StaffInvite(BaseModel):
    email: str
    full_name: str
    password: str
    user_type: str = "staff"
    role_slugs: list[str] = []


class PlatformLoginRequest(BaseModel):
    email: str
    password: str


class PlatformTokenResponse(BaseModel):
    access_token: str


class TenantCreate(BaseModel):
    name: str
    slug: str
    base_currency: str = "USD"
    timezone: str = "UTC"
