import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9_-]+$")
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class RolePermissionsUpdate(BaseModel):
    permission_ids: list[uuid.UUID]


class StaffRolesUpdate(BaseModel):
    role_ids: list[uuid.UUID]


class PermissionResponse(BaseModel):
    id: uuid.UUID
    codename: str
    description: str | None
    domain: str = ""
    action: str = ""

    model_config = {"from_attributes": True}

    @classmethod
    def from_permission(cls, perm: object) -> "PermissionResponse":
        resp = cls.model_validate(perm)
        parts = resp.codename.split(":")
        resp.domain = parts[0] if len(parts) >= 1 else ""
        resp.action = parts[2] if len(parts) >= 3 else ""
        return resp


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_system: bool
    created_at: datetime
    permissions: list[PermissionResponse] = []

    model_config = {"from_attributes": True}


class PermissionGroup(BaseModel):
    domain: str
    label: str
    permissions: list[PermissionResponse]


class PermissionOverrideResponse(BaseModel):
    permission_id: uuid.UUID
    codename: str
    description: str | None
    granted: bool


class EffectivePermissionsResponse(BaseModel):
    role_permissions: list[PermissionResponse]
    overrides: list[PermissionOverrideResponse]
    effective: list[str]


class OverrideEntry(BaseModel):
    permission_id: uuid.UUID
    granted: bool


class PermissionOverrideUpdate(BaseModel):
    overrides: list[OverrideEntry]
