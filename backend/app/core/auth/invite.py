import json

from app.config import get_settings
from app.redis_client import get_redis


async def store_invite_token(token: str, user_id: str, tenant_id: str) -> None:
    settings = get_settings()
    r = get_redis()
    ttl = settings.invite_token_expire_hours * 3600
    data = json.dumps({"user_id": user_id, "tenant_id": tenant_id})
    await r.setex(f"invite:{token}", ttl, data)
    await r.setex(f"invite_user:{user_id}", ttl, token)


async def delete_user_invite_tokens(user_id: str) -> None:
    r = get_redis()
    old_token = await r.getdel(f"invite_user:{user_id}")
    if old_token:
        await r.delete(f"invite:{old_token}")


async def get_invite_data(token: str) -> dict | None:
    r = get_redis()
    data = await r.get(f"invite:{token}")
    if data is None:
        return None
    return json.loads(data)


async def claim_invite_token(token: str) -> dict | None:
    r = get_redis()
    data = await r.getdel(f"invite:{token}")
    if data is None:
        return None
    return json.loads(data)


async def delete_invite_token(token: str) -> None:
    r = get_redis()
    await r.delete(f"invite:{token}")


async def store_reset_token(token: str, user_id: str, tenant_id: str) -> None:
    r = get_redis()
    ttl = 3600
    data = json.dumps({"user_id": user_id, "tenant_id": tenant_id})
    old_token = await r.getdel(f"pwreset_user:{user_id}")
    if old_token:
        await r.delete(f"pwreset:{old_token}")
    await r.setex(f"pwreset:{token}", ttl, data)
    await r.setex(f"pwreset_user:{user_id}", ttl, token)


async def claim_reset_token(token: str) -> dict | None:
    r = get_redis()
    data = await r.getdel(f"pwreset:{token}")
    if data is None:
        return None
    return json.loads(data)
