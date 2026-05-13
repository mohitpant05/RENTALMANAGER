from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.admin.platform_auth import get_current_platform_user
from app.core.auth.models import PlatformUser
from app.core.currency.service import (
    SUPPORTED_CURRENCIES,
    convert,
    fetch_rates,
    from_usd,
    get_all_overrides,
    remove_rate_override,
    set_rate_override,
    to_usd,
)

router = APIRouter(prefix="/api/currency", tags=["currency"])


@router.get("/rates")
async def get_rates(base: str = Query(default="USD")):
    base = base.upper()
    if base not in SUPPORTED_CURRENCIES:
        base = "USD"
    rates = await fetch_rates(base)
    return {"base": base, "rates": rates}


@router.get("/convert")
async def convert_amount(
    amount: float = Query(...),
    from_currency: str = Query(default="USD"),
    to_currency: str = Query(default="INR"),
):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    rates = await fetch_rates("USD")
    from_rate = rates.get(from_currency, 1.0)
    to_rate = rates.get(to_currency, 1.0)
    converted = convert(amount, from_rate, to_rate)
    return {
        "amount": amount,
        "from": from_currency,
        "to": to_currency,
        "converted": converted,
        "rate": round(to_rate / from_rate, 6) if from_rate else 0,
    }


@router.get("/supported")
async def supported_currencies():
    return {"currencies": SUPPORTED_CURRENCIES}


class RateOverrideRequest(BaseModel):
    currency: str
    rate_to_usd: float


@router.get("/overrides")
async def list_overrides(
    _: PlatformUser = Depends(get_current_platform_user),
):
    overrides = await get_all_overrides()
    return {"overrides": overrides}


@router.put("/overrides")
async def upsert_override(
    data: RateOverrideRequest,
    _: PlatformUser = Depends(get_current_platform_user),
):
    await set_rate_override(data.currency, data.rate_to_usd)
    return {"currency": data.currency.upper(), "rate_to_usd": data.rate_to_usd}


@router.delete("/overrides/{currency}")
async def delete_override(
    currency: str,
    _: PlatformUser = Depends(get_current_platform_user),
):
    await remove_rate_override(currency)
    return {"deleted": currency.upper()}


@router.get("/to-usd")
async def convert_to_usd(
    amount: float = Query(...),
    from_currency: str = Query(default="INR"),
):
    converted = await to_usd(amount, from_currency)
    return {"amount": amount, "from": from_currency.upper(), "usd": converted}


@router.get("/from-usd")
async def convert_from_usd(
    amount: float = Query(...),
    to_currency: str = Query(default="INR"),
):
    converted = await from_usd(amount, to_currency)
    return {"amount": amount, "to": to_currency.upper(), "converted": converted}
