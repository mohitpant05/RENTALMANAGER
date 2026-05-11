import json
import logging

import httpx

from app.redis_client import get_redis

logger = logging.getLogger(__name__)

CACHE_KEY = "currency:rates"
CACHE_TTL = 3600  # 1 hour

SUPPORTED_CURRENCIES = [
    "USD", "EUR", "GBP", "INR", "AUD", "CAD", "JPY", "CNY",
    "CHF", "SGD", "AED", "SAR", "BRL", "MXN", "ZAR", "THB",
    "KRW", "TRY", "RUB", "NZD", "SEK", "NOK", "DKK", "HKD",
    "MYR", "PHP", "IDR", "VND", "EGP", "NGN", "KES", "PKR",
]

API_URL = "https://api.exchangerate.host/latest"


async def fetch_rates(base: str = "USD") -> dict[str, float]:
    redis = get_redis()

    cache_key = f"{CACHE_KEY}:{base}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(API_URL, params={"base": base})
            resp.raise_for_status()
            data = resp.json()

        rates = {}
        source_rates = data.get("rates", {})
        for code in SUPPORTED_CURRENCIES:
            if code in source_rates:
                rates[code] = round(source_rates[code], 6)
        rates[base] = 1.0

        await redis.set(cache_key, json.dumps(rates), ex=CACHE_TTL)
        return rates
    except Exception as e:
        logger.warning("Failed to fetch exchange rates: %s", e)
        return {base: 1.0}


def convert(amount: float, from_rate: float, to_rate: float) -> float:
    if from_rate == 0:
        return 0.0
    return round(amount / from_rate * to_rate, 2)
