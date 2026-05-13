import uuid
from datetime import UTC, datetime, timedelta

from jose import jwt

from app.config import get_settings
from app.redis_client import get_redis


def create_access_token(user_id: str, tenant_id: str, roles: list[str]) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": roles,
        "type": "access",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str, tenant_id: str) -> tuple[str, str]:
    settings = get_settings()
    jti = str(uuid.uuid4())
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "type": "refresh",
        "exp": expire,
        "jti": jti,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])


async def store_refresh_token(jti: str, user_id: str, tenant_id: str) -> None:
    settings = get_settings()
    r = get_redis()
    ttl = settings.refresh_token_expire_days * 86400
    await r.setex(f"refresh:{jti}", ttl, f"{user_id}:{tenant_id}")


async def is_refresh_token_valid(jti: str) -> bool:
    r = get_redis()
    return await r.exists(f"refresh:{jti}") > 0


async def revoke_refresh_token(jti: str) -> None:
    r = get_redis()
    await r.delete(f"refresh:{jti}")
