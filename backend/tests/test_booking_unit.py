import uuid
from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from app.domains.bookings.models import TENANT_BOOKING_TABLES, Booking
from app.domains.bookings.schemas import BookingCreate, BookingListParams
from app.domains.bookings.state_machine import (
    ALL_STATUSES,
    TERMINAL_STATUSES,
    calculate_refund_percent,
    can_transition,
)

_FULL_POLICY = {
    "free_cancel_hours": 48,
    "partial_cancel_hours": 24,
    "partial_refund_percent": 50,
    "no_refund_after": True,
}


def test_can_transition_pending_to_confirmed():
    assert can_transition("pending", "confirmed") is True


def test_can_transition_pending_to_rejected():
    assert can_transition("pending", "rejected") is True


def test_can_transition_pending_to_cancelled():
    assert can_transition("pending", "cancelled") is True


def test_cannot_transition_pending_to_active():
    assert can_transition("pending", "active") is False


def test_can_transition_confirmed_to_active():
    assert can_transition("confirmed", "active") is True


def test_can_transition_confirmed_to_cancelled():
    assert can_transition("confirmed", "cancelled") is True


def test_cannot_transition_confirmed_to_rejected():
    assert can_transition("confirmed", "rejected") is False


def test_can_transition_active_to_completed():
    assert can_transition("active", "completed") is True


def test_can_transition_active_to_no_show():
    assert can_transition("active", "no_show") is True


def test_can_transition_active_to_cancelled():
    assert can_transition("active", "cancelled") is True


def test_cannot_transition_from_terminal_states():
    for terminal in TERMINAL_STATUSES:
        for target in ALL_STATUSES:
            assert can_transition(terminal, target) is False


def test_all_statuses_complete():
    assert ALL_STATUSES == {
        "pending", "confirmed", "rejected", "active",
        "completed", "cancelled", "no_show",
    }


def test_terminal_statuses():
    assert TERMINAL_STATUSES == {"rejected", "completed", "cancelled", "no_show"}


def test_refund_full_when_no_policy():
    start = datetime.now(UTC) + timedelta(hours=100)
    assert calculate_refund_percent(None, start) == 100.0


def test_refund_full_within_free_cancel_window():
    policy = _FULL_POLICY
    now = datetime.now(UTC)
    start = now + timedelta(hours=72)
    assert calculate_refund_percent(policy, start, now=now) == 100.0


def test_refund_partial_within_partial_window():
    policy = _FULL_POLICY
    now = datetime.now(UTC)
    start = now + timedelta(hours=30)
    assert calculate_refund_percent(policy, start, now=now) == 50.0


def test_refund_zero_past_all_windows():
    policy = _FULL_POLICY
    now = datetime.now(UTC)
    start = now + timedelta(hours=10)
    assert calculate_refund_percent(policy, start, now=now) == 0.0


def test_refund_full_when_no_refund_after_false():
    policy = {"free_cancel_hours": 48, "partial_cancel_hours": 0, "no_refund_after": False}
    now = datetime.now(UTC)
    start = now + timedelta(hours=10)
    assert calculate_refund_percent(policy, start, now=now) == 100.0


def test_refund_exactly_at_free_cancel_boundary():
    policy = _FULL_POLICY
    now = datetime.now(UTC)
    start = now + timedelta(hours=48)
    assert calculate_refund_percent(policy, start, now=now) == 100.0


def test_refund_just_below_free_cancel_boundary():
    policy = _FULL_POLICY
    now = datetime.now(UTC)
    start = now + timedelta(hours=47, minutes=59)
    assert calculate_refund_percent(policy, start, now=now) == 50.0


def test_booking_model_defaults():
    b = Booking(
        resource_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(days=1),
        total_price=100.0,
    )
    assert b.status == "pending"
    assert b.currency == "USD"
    assert b.version == 1
    assert b.auto_confirm is True
    assert b.hold_token is None


def test_tenant_booking_tables():
    assert TENANT_BOOKING_TABLES == {"bookings"}


def test_booking_create_schema_valid():
    data = BookingCreate(
        resource_id=uuid.uuid4(),
        hold_token="tok-123",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(days=1),
    )
    assert data.auto_confirm is True
    assert data.notes is None


def test_booking_list_params_invalid_status():
    try:
        BookingListParams(status="invalid_status")
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_booking_list_params_limit_bounds():
    try:
        BookingListParams(limit=0)
        assert False, "Should have raised"
    except ValidationError:
        pass

    try:
        BookingListParams(limit=101)
        assert False, "Should have raised"
    except ValidationError:
        pass
