from datetime import UTC, datetime

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "rejected", "cancelled"},
    "confirmed": {"active", "cancelled"},
    "active": {"completed", "cancelled", "no_show"},
}

ALL_STATUSES = {"pending", "confirmed", "rejected", "active", "completed", "cancelled", "no_show"}
TERMINAL_STATUSES = {"rejected", "completed", "cancelled", "no_show"}


def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


def calculate_refund_percent(
    cancellation_policy: dict | None,
    start_time: datetime,
    now: datetime | None = None,
) -> float:
    if cancellation_policy is None:
        return 100.0

    if now is None:
        now = datetime.now(UTC)

    hours_until_start = (start_time - now).total_seconds() / 3600

    free_cancel_hours = cancellation_policy.get("free_cancel_hours", 0)
    partial_cancel_hours = cancellation_policy.get("partial_cancel_hours", 0)
    partial_refund_percent = cancellation_policy.get("partial_refund_percent", 0)
    no_refund_after = cancellation_policy.get("no_refund_after", False)

    if hours_until_start >= free_cancel_hours > 0:
        return 100.0
    if hours_until_start >= partial_cancel_hours > 0:
        return float(partial_refund_percent)
    if no_refund_after:
        return 0.0
    return 100.0
