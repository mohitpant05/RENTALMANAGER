import json
import logging

import httpx

from app.redis_client import get_redis

logger = logging.getLogger(__name__)

CACHE_KEY = "currency:rates"
CACHE_TTL = 3600  # 1 hour
OVERRIDE_KEY = "currency:overrides"

SUPPORTED_CURRENCIES = [
    "USD", "EUR", "GBP", "INR", "AUD", "CAD", "JPY", "CNY",
    "CHF", "SGD", "AED", "SAR", "BRL", "MXN", "ZAR", "THB",
    "KRW", "TRY", "RUB", "NZD", "SEK", "NOK", "DKK", "HKD",
    "MYR", "PHP", "IDR", "VND", "EGP", "NGN", "KES", "PKR",
]

API_URL = "https://api.frankfurter.dev/v1/latest"


async def fetch_rates(base: str = "USD") -> dict[str, float]:
    redis = get_redis()

    cache_key = f"{CACHE_KEY}:{base}"
    cached = await redis.get(cache_key)
    if cached:
        rates = json.loads(cached)
    else:
        rates = await _fetch_from_api(base)
        if rates:
            await redis.set(cache_key, json.dumps(rates), ex=CACHE_TTL)

    overrides = await _get_overrides()
    if base == "USD" and overrides:
        rates.update(overrides)

    return rates


async def _fetch_from_api(base: str) -> dict[str, float]:
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
        return rates
    except Exception as e:
        logger.warning("Failed to fetch exchange rates: %s", e)
        return {base: 1.0}


async def _get_overrides() -> dict[str, float]:
    redis = get_redis()
    cached = await redis.get(OVERRIDE_KEY)
    if cached:
        return json.loads(cached)
    return {}


async def set_rate_override(currency: str, rate_to_usd: float) -> None:
    redis = get_redis()
    overrides = await _get_overrides()
    overrides[currency.upper()] = round(rate_to_usd, 6)
    await redis.set(OVERRIDE_KEY, json.dumps(overrides))
    await redis.delete(f"{CACHE_KEY}:USD")


async def remove_rate_override(currency: str) -> None:
    redis = get_redis()
    overrides = await _get_overrides()
    overrides.pop(currency.upper(), None)
    await redis.set(OVERRIDE_KEY, json.dumps(overrides))
    await redis.delete(f"{CACHE_KEY}:USD")


async def get_all_overrides() -> dict[str, float]:
    return await _get_overrides()


def convert(amount: float, from_rate: float, to_rate: float) -> float:
    if from_rate == 0:
        return 0.0
    return round(amount / from_rate * to_rate, 2)


async def to_usd(amount: float, from_currency: str) -> float:
    if from_currency.upper() == "USD":
        return round(amount, 2)
    rates = await fetch_rates("USD")
    from_rate = rates.get(from_currency.upper(), 1.0)
    return convert(amount, from_rate, 1.0)


async def from_usd(amount: float, to_currency: str) -> float:
    if to_currency.upper() == "USD":
        return round(amount, 2)
    rates = await fetch_rates("USD")
    to_rate = rates.get(to_currency.upper(), 1.0)
    return convert(amount, 1.0, to_rate)


async def refresh_rates_cache() -> int:
    redis = get_redis()
    await redis.delete(f"{CACHE_KEY}:USD")
    rates = await fetch_rates("USD")
    return len(rates)
