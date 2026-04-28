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
            duration_minutes = (end - start).total_seconds() / 60
            allowed = [_parse_duration(d) for d in slot_config.get("duration_options", [])]
            if allowed and not any(abs(duration_minutes - a) < 1 for a in allowed):
                errors.append(
                    f"Slot duration {duration_minutes:.0f}min not in allowed: "
                    f"{slot_config.get('duration_options')}"
                )
        return errors

    async def check(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime
    ) -> bool:
        return await check_overlap(session, resource_id, start, end)

    async def hold(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        hold_minutes: int = 10,
    ) -> HoldResult:
        available = await self.check(session, resource_id, start, end)
        if not available:
            raise ValueError("Time slot not available")
        return await create_hold(session, resource_id, start, end, hold_minutes)
