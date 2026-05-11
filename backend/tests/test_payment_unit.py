import uuid

from app.core.payments.models import TENANT_PAYMENT_TABLES, Payment


def test_payment_model_defaults():
    p = Payment(
        booking_id=uuid.uuid4(),
        amount=1000.0,
        currency="INR",
        provider="manual",
    )
    assert p.status == "pending"
    assert p.provider_ref is None
    assert p.paid_at is None
    assert p.refund_amount is None


def test_payment_valid_statuses():
    valid = {"pending", "paid", "failed", "refunded", "partially_refunded"}
    for s in valid:
        p = Payment(
            booking_id=uuid.uuid4(),
            amount=100.0,
            currency="USD",
            provider="manual",
            status=s,
        )
        assert p.status == s


def test_tenant_payment_tables():
    assert "payments" in TENANT_PAYMENT_TABLES
