import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class TenantTheme(SQLModel, table=True):
    __tablename__ = "tenant_themes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", unique=True, index=True)
    brand: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    colors: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    typography: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    components: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    features: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
