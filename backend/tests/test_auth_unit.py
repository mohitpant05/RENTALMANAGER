from app.core.auth.password import hash_password, verify_password


def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("testpassword123")
    assert hashed != "testpassword123"
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("testpassword123")
    assert verify_password("testpassword123", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("testpassword123")
    assert verify_password("wrongpassword", hashed) is False


def test_hash_password_unique_salts():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2


from datetime import UTC

from jose import jwt

from app.core.auth.dependencies import matches_permission
from app.core.auth.jwt import create_access_token, create_refresh_token, decode_token


def test_create_access_token_structure():
    token = create_access_token(
        user_id="user-123",
        tenant_id="tenant-456",
        roles=["admin"],
    )
    payload = jwt.decode(token, "dev-secret-key-change-in-production", algorithms=["HS256"])
    assert payload["sub"] == "user-123"
    assert payload["tenant_id"] == "tenant-456"
    assert payload["roles"] == ["admin"]
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "jti" in payload


def test_create_refresh_token_returns_token_and_jti():
    token, jti = create_refresh_token(user_id="user-123", tenant_id="tenant-456")
    payload = jwt.decode(token, "dev-secret-key-change-in-production", algorithms=["HS256"])
    assert payload["sub"] == "user-123"
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_decode_token_valid():
    token = create_access_token(
        user_id="user-123",
        tenant_id="tenant-456",
        roles=["staff"],
    )
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_decode_token_expired():
    from datetime import datetime, timedelta

    from jose import jwt as jose_jwt

    payload = {
        "sub": "user-123",
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(hours=1),
    }
    token = jose_jwt.encode(payload, "dev-secret-key-change-in-production", algorithm="HS256")
    try:
        decode_token(token)
        assert False, "Should have raised"
    except Exception:
        pass


def test_exact_permission_match():
    granted = {"resources:vehicles:manage"}
    assert matches_permission("resources:vehicles:manage", granted) is True


def test_permission_no_match():
    granted = {"resources:vehicles:manage"}
    assert matches_permission("resources:venues:manage", granted) is False


def test_wildcard_qualifier_match():
    granted = {"resources:*:read"}
    assert matches_permission("resources:vehicles:read", granted) is True


def test_wildcard_action_match():
    granted = {"resources:vehicles:*"}
    assert matches_permission("resources:vehicles:manage", granted) is True


def test_full_wildcard_match():
    granted = {"*:*:*"}
    assert matches_permission("resources:vehicles:manage", granted) is True


def test_domain_wildcard_match():
    granted = {"resources:*:*"}
    assert matches_permission("resources:vehicles:read", granted) is True


import pytest as _pytest
from pydantic import ValidationError

from app.core.auth.schemas import LoginRequest, RegisterRequest, TokenResponse


def test_register_request_valid():
    req = RegisterRequest(
        email="user@example.com",
        password="strongpass123",
        full_name="John Doe",
    )
    assert req.email == "user@example.com"


def test_register_request_invalid_email():
    with _pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="pass1234", full_name="X")


def test_register_request_short_password():
    with _pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="short", full_name="X")


def test_login_request_valid():
    req = LoginRequest(email="user@example.com", password="pass123456")
    assert req.email == "user@example.com"


def test_token_response_structure():
    resp = TokenResponse(access_token="abc", refresh_token="def")
    assert resp.token_type == "bearer"
