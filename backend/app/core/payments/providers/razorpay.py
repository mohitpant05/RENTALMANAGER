import logging

from app.core.payments.provider import PaymentResult, RefundResult

logger = logging.getLogger(__name__)


class RazorpayProvider:
    def __init__(self, config: dict):
        self.key_id = config.get("razorpay_key_id", "")
        self.key_secret = config.get("razorpay_key_secret", "")

    def _get_client(self):
        import razorpay
        return razorpay.Client(auth=(self.key_id, self.key_secret))

    async def create_payment(
        self, amount: float, currency: str, metadata: dict
    ) -> PaymentResult:
        if not self.key_id or not self.key_secret:
            return PaymentResult(success=False, error="Razorpay keys not configured")
        try:
            client = self._get_client()
            order = client.order.create({
                "amount": int(amount * 100),
                "currency": currency.upper(),
                "notes": metadata,
            })
            return PaymentResult(
                success=True,
                provider_ref=order["id"],
                provider_data={"order_id": order["id"]},
            )
        except Exception as e:
            logger.error("Razorpay create_payment failed: %s", e)
            return PaymentResult(success=False, error=str(e))

    async def confirm_payment(self, provider_ref: str) -> PaymentResult:
        try:
            client = self._get_client()
            order = client.order.fetch(provider_ref)
            return PaymentResult(
                success=order["status"] == "paid",
                provider_ref=provider_ref,
                provider_data={"status": order["status"]},
            )
        except Exception as e:
            logger.error("Razorpay confirm_payment failed: %s", e)
            return PaymentResult(success=False, error=str(e))

    async def refund_payment(
        self, provider_ref: str, amount: float
    ) -> RefundResult:
        try:
            client = self._get_client()
            payments = client.order.payments(provider_ref)
            payment_id = payments["items"][0]["id"] if payments["items"] else None
            if not payment_id:
                return RefundResult(success=False, error="No payment found for order")
            refund = client.payment.refund(payment_id, int(amount * 100))
            return RefundResult(success=True, refund_ref=refund["id"])
        except Exception as e:
            logger.error("Razorpay refund failed: %s", e)
            return RefundResult(success=False, error=str(e))

    async def verify_keys(self, config: dict) -> bool:
        try:
            import razorpay
            client = razorpay.Client(
                auth=(config.get("razorpay_key_id", ""), config.get("razorpay_key_secret", ""))
            )
            client.order.all({"count": 1})
            return True
        except Exception:
            return False
