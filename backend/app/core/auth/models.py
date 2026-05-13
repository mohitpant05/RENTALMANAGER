import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

TENANT_AUTH_TABLES: set[str] = {
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
}


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(max_length=255, index=True)
    password_hash: str | None = Field(default=None, max_length=255)
    full_name: str = Field(max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    user_type: str = Field(max_length=20)
    avatar_url: str | None = Field(default=None, max_length=500)
    preferred_currency: str = Field(default="USD", max_length=3)
    last_login: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    slug: str = Field(max_length=100, index=True)
    description: str | None = Field(default=None, max_length=500)
    is_system: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    codename: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None, max_length=500)


class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"

    role_id: uuid.UUID = Field(foreign_key="roles.id", primary_key=True)
    permission_id: uuid.UUID = Field(foreign_key="permissions.id", primary_key=True)


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: uuid.UUID = Field(foreign_key="users.id", primary_key=True)
    role_id: uuid.UUID = Field(foreign_key="roles.id", primary_key=True)
    assigned_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PlatformUser(SQLModel, table=True):
    __tablename__ = "platform_users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    full_name: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
