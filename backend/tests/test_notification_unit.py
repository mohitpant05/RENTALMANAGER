import uuid
from datetime import UTC, datetime

from app.core.notifications.events import (
    ALL_EVENT_TYPES,
    BOOKING_CONFIRMED,
    REVIEW_RECEIVED,
    booking_confirmed_payload,
    booking_new_payload,
    review_received_payload,
)
from app.core.notifications.models import TENANT_NOTIFICATION_TABLES, Notification
from app.core.notifications.schemas import (
    MarkAllReadResponse,
    NotificationResponse,
    UnreadCountResponse,
)


def test_notification_model_defaults():
    n = Notification(
        user_id=uuid.uuid4(),
        event_type="booking.confirmed",
        title="Booking Confirmed",
        body="Your booking has been confirmed",
    )
    assert n.is_read is False
    assert n.read_at is None
    assert n.payload is None


def test_tenant_notification_tables():
    assert TENANT_NOTIFICATION_TABLES == {"notifications"}


def test_all_event_types():
    assert BOOKING_CONFIRMED in ALL_EVENT_TYPES
    assert REVIEW_RECEIVED in ALL_EVENT_TYPES
    assert len(ALL_EVENT_TYPES) == 8


def test_booking_confirmed_payload():
    p = booking_confirmed_payload("booking-123", "Beach Villa")
    assert p["booking_id"] == "booking-123"
    assert p["resource_name"] == "Beach Villa"


def test_booking_new_payload():
    p = booking_new_payload("booking-456", "Mountain Lodge", "John Doe")
    assert p["booking_id"] == "booking-456"
    assert p["user_name"] == "John Doe"


def test_review_received_payload():
    p = review_received_payload("review-789", "Seaside Cabin", 5)
    assert p["review_id"] == "review-789"
    assert p["rating"] == 5


def test_notification_response_from_model():
    n = Notification(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_type="booking.confirmed",
        title="Confirmed",
        body="Your booking is confirmed",
        is_read=False,
        created_at=datetime.now(UTC),
    )
    resp = NotificationResponse.model_validate(n)
    assert resp.event_type == "booking.confirmed"
    assert resp.is_read is False


def test_unread_count_response():
    r = UnreadCountResponse(count=5)
    assert r.count == 5


def test_mark_all_read_response():
    r = MarkAllReadResponse(marked=3)
    assert r.marked == 3
