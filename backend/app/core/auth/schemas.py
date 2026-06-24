import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

PHONE_RE = re.compile(r"^\+?\d{7,15}$")


def _validate_phone(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    digits = re.sub(r"[^\d]", "", v)
    if len(digits) > 15:
        raise ValueError("Phone number must not exceed 15 digits")
    if len(digits) < 7:
        raise ValueError("Phone number must be at least 7 digits")
    if not PHONE_RE.match(v):
        raise ValueError("Phone must contain only digits, optionally prefixed with +")
    return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return _validate_phone(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    is_verified: bool
    user_type: str
    avatar_url: str | None
    preferred_currency: str
    created_at: datetime
    roles: list[str] = []
    permissions: list[str] = []


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    preferred_currency: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        return _validate_phone(v)


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class VerifyInviteResponse(BaseModel):
    valid: bool
    email: str | None = None
    full_name: str | None = None


class CustomerLookupResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: str | None
