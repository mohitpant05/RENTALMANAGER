import uuid
from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.availability.strategy import (
    HoldResult,
    check_overlap,
    create_hold,
)


class DateRangeProvider:
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
