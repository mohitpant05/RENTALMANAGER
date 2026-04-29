import json

from app.config import get_settings
from app.redis_client import get_redis


async def store_invite_token(token: str, user_id: str, tenant_id: str) -> None:
    settings = get_settings()
    r = get_redis()
    ttl = settings.invite_token_expire_hours * 3600
    data = json.dumps({"user_id": user_id, "tenant_id": tenant_id})
    await r.setex(f"invite:{token}", ttl, data)


async def get_invite_data(token: str) -> dict | None:
    r = get_redis()
    data = await r.get(f"invite:{token}")
    if data is None:
        return None
    return json.loads(data)


async def delete_invite_token(token: str) -> None:
    r = get_redis()
    await r.delete(f"invite:{token}")
