import uuid
from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.availability.strategy import (
    HoldResult,
    check_overlap,
    create_hold,
)

MINIMUM_HOURS = 0.5


class HourlyProvider:
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

        hours = (end - start).total_seconds() / 3600
        if hours < MINIMUM_HOURS:
            errors.append(f"Minimum booking duration is {MINIMUM_HOURS} hours")
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
            raise ValueError("Resource not available for requested hours")
        return await create_hold(session, resource_id, start, end, hold_minutes)
