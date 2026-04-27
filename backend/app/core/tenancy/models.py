import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100, unique=True, index=True)
    schema_name: str = Field(max_length=100, unique=True)
    is_active: bool = Field(default=True)
    config: dict | None = Field(default=None, sa_column=Column(JSONB))
    base_currency: str = Field(default="USD", max_length=3)
    timezone: str = Field(default="UTC", max_length=50)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TenantDomain(SQLModel, table=True):
    __tablename__ = "tenant_domains"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    domain: str = Field(max_length=255, unique=True, index=True)
    is_primary: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PlatformConfig(SQLModel, table=True):
    __tablename__ = "platform_config"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    key: str = Field(max_length=100, unique=True, index=True)
    value: str = Field(sa_column=Column(Text))
    description: str | None = Field(default=None, max_length=500)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
