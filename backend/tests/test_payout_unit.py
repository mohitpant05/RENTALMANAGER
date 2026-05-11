import uuid

from app.core.payouts.models import TENANT_PAYOUT_TABLES, Payout, PayoutItem


def test_payout_model_defaults():
    p = Payout(
        owner_id=uuid.uuid4(),
        amount=5000.0,
        currency="INR",
    )
    assert p.status == "pending"
    assert p.settled_at is None
    assert p.settled_by is None


def test_payout_item_model():
    item = PayoutItem(
        payout_id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        booking_total=1000.0,
        commission=50.0,
        owner_amount=950.0,
    )
    assert item.booking_total == 1000.0
    assert item.owner_amount == 950.0


def test_tenant_payout_tables():
    assert "payouts" in TENANT_PAYOUT_TABLES
    assert "payout_items" in TENANT_PAYOUT_TABLES
