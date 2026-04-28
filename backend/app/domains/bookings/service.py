import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.bookings.models import Booking
from app.domains.bookings.schemas import BookingCreate
from app.domains.bookings.state_machine import (
    calculate_refund_percent,
    can_transition,
)
from app.domains.resources.availability.strategy import confirm_hold, release_hold
from app.domains.resources.models import Resource, ResourceType
from app.domains.resources.pricing.strategy import get_pricing_provider


async def create_booking(
    session: AsyncSession,
    data: BookingCreate,
    user_id: uuid.UUID,
) -> Booking:
    result = await session.exec(
        select(Resource).where(Resource.id == data.resource_id)
    )
    resource = result.first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    if resource.status != "active":
        raise HTTPException(status_code=400, detail="Resource is not active")

    result = await session.exec(
        select(ResourceType).where(ResourceType.id == resource.type_id)
    )
    resource_type = result.first()
    if resource_type is None:
        raise HTTPException(status_code=404, detail="Resource type not found")

    pricing = get_pricing_provider(resource_type.pricing_model)
    total_price = pricing.calculate(
        resource.base_price, data.start_time, data.end_time, resource_type.pricing_config
    )

    cancellation_policy = resource_type.cancellation_defaults

    booking = Booking(
        resource_id=data.resource_id,
        user_id=user_id,
        status="pending",
        start_time=data.start_time,
        end_time=data.end_time,
        total_price=total_price,
        currency=resource.currency,
        hold_token=data.hold_token,
        cancellation_policy=cancellation_policy,
        notes=data.notes,
        auto_confirm=data.auto_confirm,
    )

    confirmed = await confirm_hold(session, data.hold_token, booking.id)
    if not confirmed:
        raise HTTPException(
            status_code=409,
            detail="Hold token invalid or expired — please create a new hold",
        )

    if data.auto_confirm:
        booking.status = "confirmed"
        booking.confirmed_at = datetime.now(UTC)

    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def get_booking(
    session: AsyncSession, booking_id: uuid.UUID, *, for_update: bool = False
) -> Booking:
    stmt = select(Booking).where(Booking.id == booking_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.exec(stmt)
    booking = result.first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


async def list_bookings(
    session: AsyncSession,
    user_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    resource_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Booking]:
    stmt = select(Booking)
    if user_id:
        stmt = stmt.where(Booking.user_id == user_id)
    if status_filter:
        stmt = stmt.where(Booking.status == status_filter)
    if resource_id:
        stmt = stmt.where(Booking.resource_id == resource_id)
    stmt = stmt.offset(offset).limit(limit).order_by(Booking.created_at.desc())
    result = await session.exec(stmt)
    return list(result.all())


async def confirm_booking(
    session: AsyncSession, booking_id: uuid.UUID
) -> Booking:
    booking = await get_booking(session, booking_id, for_update=True)
    if not can_transition(booking.status, "confirmed"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot confirm booking in '{booking.status}' state",
        )
    booking.status = "confirmed"
    booking.confirmed_at = datetime.now(UTC)
    booking.updated_at = datetime.now(UTC)
    booking.version += 1
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def reject_booking(
    session: AsyncSession, booking_id: uuid.UUID, reason: str | None = None
) -> Booking:
    booking = await get_booking(session, booking_id, for_update=True)
    if not can_transition(booking.status, "rejected"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject booking in '{booking.status}' state",
        )
    booking.status = "rejected"
    booking.cancellation_reason = reason
    booking.updated_at = datetime.now(UTC)
    booking.version += 1

    if booking.hold_token:
        await release_hold(session, booking.hold_token)

    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def cancel_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
    user_id: uuid.UUID,
    is_admin: bool = False,
    reason: str | None = None,
) -> Booking:
    booking = await get_booking(session, booking_id, for_update=True)

    if not is_admin and booking.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not the booking owner")

    if not can_transition(booking.status, "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel booking in '{booking.status}' state",
        )

    refund = calculate_refund_percent(
        booking.cancellation_policy, booking.start_time
    )

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(UTC)
    booking.cancellation_reason = reason
    booking.refund_percent = refund
    booking.updated_at = datetime.now(UTC)
    booking.version += 1

    if booking.hold_token:
        await release_hold(session, booking.hold_token)

    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


async def mark_no_show(
    session: AsyncSession, booking_id: uuid.UUID
) -> Booking:
    booking = await get_booking(session, booking_id, for_update=True)
    if not can_transition(booking.status, "no_show"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot mark no-show for booking in '{booking.status}' state",
        )
    booking.status = "no_show"
    booking.refund_percent = 0.0
    booking.updated_at = datetime.now(UTC)
    booking.version += 1
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking
