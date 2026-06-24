from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import and_, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.models import Resource, ResourceAvailability


@dataclass
class HoldResult:
    hold_token: str
    expires: datetime


class AvailabilityProvider(Protocol):
    def validate_times(
        self, start: datetime, end: datetime, slot_config: dict | None
    ) -> list[str]: ...

    async def check(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        buffer_minutes: int = 0,
    ) -> bool: ...

    async def hold(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        hold_minutes: int = 10, buffer_minutes: int = 0,
    ) -> HoldResult: ...


async def release_hold(session: AsyncSession, hold_token: str) -> bool:
    result = await session.exec(
        select(ResourceAvailability).where(
            ResourceAvailability.hold_token == hold_token,
            ResourceAvailability.status == "held",
        )
    )
    record = result.first()
    if record is None:
        return False
    await session.delete(record)
    await session.flush()
    return True


async def confirm_hold(session: AsyncSession, hold_token: str, booking_id: uuid.UUID) -> bool:
    result = await session.exec(
        select(ResourceAvailability).where(
            ResourceAvailability.hold_token == hold_token,
            ResourceAvailability.status == "held",
        ).with_for_update()
    )
    record = result.first()
    if record is None:
        return False
    now = datetime.now(UTC)
    if record.hold_expires and record.hold_expires < now:
        await session.delete(record)
        await session.flush()
        return False
    record.status = "booked"
    record.booking_id = booking_id
    record.hold_token = None
    record.hold_expires = None
    session.add(record)
    await session.flush()
    return True


async def check_overlap(
    session: AsyncSession,
    resource_id: uuid.UUID,
    start: datetime,
    end: datetime,
    buffer_minutes: int = 0,
) -> bool:
    now = datetime.now(UTC)
    buf = timedelta(minutes=buffer_minutes)
    result = await session.exec(
        select(ResourceAvailability).where(
            ResourceAvailability.resource_id == resource_id,
            ResourceAvailability.start_time < (end + buf),
            ResourceAvailability.end_time > (start - buf),
            or_(
                ResourceAvailability.status == "booked",
                and_(
                    ResourceAvailability.status == "held",
                    ResourceAvailability.hold_expires > now,
                ),
            ),
        )
    )
    return result.first() is None


async def create_hold(
    session: AsyncSession,
    resource_id: uuid.UUID,
    start: datetime,
    end: datetime,
    hold_minutes: int,
    buffer_minutes: int = 0,
) -> HoldResult:
    # Lock the resource row to serialize concurrent hold attempts
    await session.exec(
        select(Resource).where(Resource.id == resource_id).with_for_update()
    )
    # Re-check overlap under lock to prevent TOCTOU race
    available = await check_overlap(session, resource_id, start, end, buffer_minutes)
    if not available:
        raise ValueError("Resource no longer available (concurrent booking)")

    token = str(uuid.uuid4())
    expires = datetime.now(UTC) + timedelta(minutes=hold_minutes)
    record = ResourceAvailability(
        resource_id=resource_id,
        start_time=start,
        end_time=end,
        status="held",
        hold_token=token,
        hold_expires=expires,
    )
    session.add(record)
    await session.commit()
    return HoldResult(hold_token=token, expires=expires)


def get_availability_provider(model: str) -> AvailabilityProvider:
    from app.domains.resources.availability.date_range import DateRangeProvider
    from app.domains.resources.availability.hourly import HourlyProvider
    from app.domains.resources.availability.time_slot import TimeSlotProvider

    providers: dict[str, AvailabilityProvider] = {
        "date_range": DateRangeProvider(),
        "time_slot": TimeSlotProvider(),
        "hourly": HourlyProvider(),
    }
    if model not in providers:
        raise ValueError(f"Unknown availability model: {model}")
    return providers[model]
