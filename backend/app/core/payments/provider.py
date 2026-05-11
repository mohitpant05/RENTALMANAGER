from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class PaymentResult(BaseModel):
    success: bool
    provider_ref: str | None = None
    provider_data: dict | None = None
    error: str | None = None


class RefundResult(BaseModel):
    success: bool
    refund_ref: str | None = None
    error: str | None = None


class PaymentProvider(Protocol):
    async def create_payment(
        self, amount: float, currency: str, metadata: dict
    ) -> PaymentResult: ...

    async def confirm_payment(self, provider_ref: str) -> PaymentResult: ...

    async def refund_payment(
        self, provider_ref: str, amount: float
    ) -> RefundResult: ...

    async def verify_keys(self, config: dict) -> bool: ...


def get_provider(provider_name: str, config: dict | None = None) -> PaymentProvider:
    if provider_name == "stripe":
        from app.core.payments.providers.stripe import StripeProvider
        return StripeProvider(config or {})
    elif provider_name == "razorpay":
        from app.core.payments.providers.razorpay import RazorpayProvider
        return RazorpayProvider(config or {})
    else:
        from app.core.payments.providers.manual import ManualProvider
        return ManualProvider()
