BOOKING_CONFIRMED = "booking.confirmed"
BOOKING_CANCELLED = "booking.cancelled"
BOOKING_REJECTED = "booking.rejected"
BOOKING_COMPLETED = "booking.completed"
BOOKING_NEW = "booking.new"
REVIEW_RECEIVED = "review.received"
REVIEW_MODERATED = "review.moderated"
RESOURCE_APPROVED = "resource.approved"
EMAIL_FAILED = "email.failed"
STAFF_INVITED = "staff.invited"

ALL_EVENT_TYPES = {
    BOOKING_CONFIRMED,
    BOOKING_CANCELLED,
    BOOKING_REJECTED,
    BOOKING_COMPLETED,
    BOOKING_NEW,
    REVIEW_RECEIVED,
    REVIEW_MODERATED,
    RESOURCE_APPROVED,
    EMAIL_FAILED,
    STAFF_INVITED,
}


def booking_confirmed_payload(booking_id: str, resource_name: str) -> dict:
    return {
        "booking_id": booking_id,
        "resource_name": resource_name,
    }


def booking_cancelled_payload(
    booking_id: str, resource_name: str, reason: str | None = None
) -> dict:
    return {
        "booking_id": booking_id,
        "resource_name": resource_name,
        "reason": reason,
    }


def booking_new_payload(booking_id: str, resource_name: str, user_name: str) -> dict:
    return {
        "booking_id": booking_id,
        "resource_name": resource_name,
        "user_name": user_name,
    }


def review_received_payload(
    review_id: str, resource_name: str, rating: int
) -> dict:
    return {
        "review_id": review_id,
        "resource_name": resource_name,
        "rating": rating,
    }
