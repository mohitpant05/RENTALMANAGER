from app.core.payments.provider import PaymentResult, RefundResult


class ManualProvider:
    async def create_payment(
        self, amount: float, currency: str, metadata: dict
    ) -> PaymentResult:
        return PaymentResult(success=True, provider_ref=None)

    async def confirm_payment(self, provider_ref: str) -> PaymentResult:
        return PaymentResult(success=True, provider_ref=provider_ref)

    async def refund_payment(
        self, provider_ref: str, amount: float
    ) -> RefundResult:
        return RefundResult(success=True, refund_ref=None)

    async def verify_keys(self, config: dict) -> bool:
        return True
