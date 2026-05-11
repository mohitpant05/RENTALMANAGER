import logging

from app.core.payments.provider import PaymentResult, RefundResult

logger = logging.getLogger(__name__)


class StripeProvider:
    def __init__(self, config: dict):
        self.secret_key = config.get("stripe_secret_key", "")
        self.publishable_key = config.get("stripe_publishable_key", "")

    async def create_payment(
        self, amount: float, currency: str, metadata: dict
    ) -> PaymentResult:
        if not self.secret_key:
            return PaymentResult(success=False, error="Stripe secret key not configured")
        try:
            import stripe
            stripe.api_key = self.secret_key
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency.lower(),
                metadata=metadata,
            )
            return PaymentResult(
                success=True,
                provider_ref=intent.id,
                provider_data={"client_secret": intent.client_secret},
            )
        except Exception as e:
            logger.error("Stripe create_payment failed: %s", e)
            return PaymentResult(success=False, error=str(e))

    async def confirm_payment(self, provider_ref: str) -> PaymentResult:
        try:
            import stripe
            stripe.api_key = self.secret_key
            intent = stripe.PaymentIntent.retrieve(provider_ref)
            return PaymentResult(
                success=intent.status == "succeeded",
                provider_ref=provider_ref,
                provider_data={"status": intent.status},
            )
        except Exception as e:
            logger.error("Stripe confirm_payment failed: %s", e)
            return PaymentResult(success=False, error=str(e))

    async def refund_payment(
        self, provider_ref: str, amount: float
    ) -> RefundResult:
        try:
            import stripe
            stripe.api_key = self.secret_key
            refund = stripe.Refund.create(
                payment_intent=provider_ref,
                amount=int(amount * 100),
            )
            return RefundResult(success=True, refund_ref=refund.id)
        except Exception as e:
            logger.error("Stripe refund failed: %s", e)
            return RefundResult(success=False, error=str(e))

    async def verify_keys(self, config: dict) -> bool:
        try:
            import stripe
            stripe.api_key = config.get("stripe_secret_key", "")
            stripe.Account.retrieve()
            return True
        except Exception:
            return False
