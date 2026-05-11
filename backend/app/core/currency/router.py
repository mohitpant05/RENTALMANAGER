from fastapi import APIRouter, Query

from app.core.currency.service import SUPPORTED_CURRENCIES, convert, fetch_rates

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
