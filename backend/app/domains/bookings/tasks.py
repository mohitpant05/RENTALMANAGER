from datetime import UTC, datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.bookings.models import Booking
from app.domains.resources.models import ResourceAvailability


async def cleanup_expired_holds(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    result = await session.exec(
        select(ResourceAvailability).where(
            ResourceAvailability.status == "held",
            ResourceAvailability.hold_expires < now,
        )
    )
    expired = list(result.all())
    for record in expired:
        await session.delete(record)
    if expired:
        await session.commit()
    return len(expired)


async def activate_confirmed_bookings(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    result = await session.exec(
        select(Booking).where(
            Booking.status == "confirmed",
            Booking.start_time <= now,
        )
    )
    bookings = list(result.all())
    for booking in bookings:
        booking.status = "active"
        booking.updated_at = now
        booking.version += 1
        session.add(booking)
    if bookings:
        await session.commit()
    return len(bookings)


async def complete_active_bookings(session: AsyncSession) -> int:
    now = datetime.now(UTC)
    result = await session.exec(
        select(Booking).where(
            Booking.status == "active",
            Booking.end_time <= now,
        )
    )
    bookings = list(result.all())
    for booking in bookings:
        booking.status = "completed"
        booking.updated_at = now
        booking.version += 1
        session.add(booking)
    if bookings:
        await session.commit()
    return len(bookings)
