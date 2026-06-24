import re
import uuid
from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.availability.strategy import (
    HoldResult,
    check_overlap,
    create_hold,
)


def _parse_duration(s: str) -> float:
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(h|min)$", s)
    if not match:
        return 0
    val, unit = float(match.group(1)), match.group(2)
    return val * 60 if unit == "h" else val


class TimeSlotProvider:
    def validate_times(
        self, start: datetime, end: datetime, slot_config: dict | None
    ) -> list[str]:
        errors: list[str] = []
        now = datetime.now(UTC)
        if start < now:
            errors.append("Start time cannot be in the past")
        if end <= start:
            errors.append("End time must be after start time")
            return errors

        if slot_config:
            fixed_slots = slot_config.get("fixed_slots")
            if fixed_slots:
                start_hhmm = start.strftime("%H:%M")
                end_hhmm = end.strftime("%H:%M")
                matched = any(
                    s.get("start") == start_hhmm and s.get("end") == end_hhmm
                    for s in fixed_slots
                )
                if not matched:
                    labels = [f"{s['start']}-{s['end']}" for s in fixed_slots]
                    errors.append(
                        f"Time {start_hhmm}-{end_hhmm} not in allowed slots: {labels}"
                    )
            else:
                duration_minutes = (end - start).total_seconds() / 60
                allowed = [_parse_duration(d) for d in slot_config.get("duration_options", [])]
                if allowed and not any(abs(duration_minutes - a) < 1 for a in allowed):
                    errors.append(
                        f"Slot duration {duration_minutes:.0f}min not in allowed: "
                        f"{slot_config.get('duration_options')}"
                    )
        return errors

    async def check(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        buffer_minutes: int = 0,
    ) -> bool:
        return await check_overlap(session, resource_id, start, end, buffer_minutes)

    async def hold(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        hold_minutes: int = 10, buffer_minutes: int = 0,
    ) -> HoldResult:
        return await create_hold(session, resource_id, start, end, hold_minutes, buffer_minutes)
