import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import User
from app.core.payments.models import Payment
from app.core.payouts.models import Payout, PayoutItem
from app.core.payouts.schemas import OwnerBalance
from app.domains.bookings.models import Booking
from app.domains.resources.models import Resource


async def get_owner_balances(session: AsyncSession) -> list[OwnerBalance]:
    settled_booking_ids_subq = (
        select(PayoutItem.booking_id)
        .join(Payout, PayoutItem.payout_id == Payout.id)
        .where(Payout.status == "settled")
    )

    result = await session.exec(
        select(
            Resource.owner_id,
            func.sum(Booking.owner_payout).label("pending_amount"),
            func.count(Booking.id).label("booking_count"),
            Booking.currency,
        )
        .join(Resource, Booking.resource_id == Resource.id)
        .join(Payment, Payment.booking_id == Booking.id)
        .where(
            Booking.status == "completed",
            Payment.status == "paid",
            Booking.id.notin_(settled_booking_ids_subq),
        )
        .group_by(Resource.owner_id, Booking.currency)
    )
    rows = list(result.all())

    balances = []
    for row in rows:
        owner_id, pending_amount, booking_count, currency = row
        user_result = await session.exec(
            select(User).where(User.id == owner_id)
        )
        user = user_result.first()

        last_payout_result = await session.exec(
            select(Payout)
            .where(Payout.owner_id == owner_id, Payout.status == "settled")
            .order_by(Payout.settled_at.desc())
            .limit(1)
        )
        last_payout = last_payout_result.first()

        balances.append(OwnerBalance(
            owner_id=owner_id,
            owner_name=user.full_name if user else "Unknown",
            owner_email=user.email if user else "",
            pending_amount=pending_amount or 0.0,
            currency=currency,
            booking_count=booking_count,
            last_settled=last_payout.settled_at if last_payout else None,
        ))

    return balances


async def get_unsettled_bookings(
    session: AsyncSession,
    owner_id: uuid.UUID,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    currency: str | None = None,
) -> list[Booking]:
    settled_booking_ids_subq = (
        select(PayoutItem.booking_id)
        .join(Payout, PayoutItem.payout_id == Payout.id)
        .where(Payout.status == "settled")
    )

    stmt = (
        select(Booking)
        .join(Resource, Booking.resource_id == Resource.id)
        .join(Payment, Payment.booking_id == Booking.id)
        .where(
            Resource.owner_id == owner_id,
            Booking.status == "completed",
            Payment.status == "paid",
            Booking.id.notin_(settled_booking_ids_subq),
        )
    )
    if period_start:
        stmt = stmt.where(Booking.end_time >= period_start)
    if period_end:
        stmt = stmt.where(Booking.end_time <= period_end)
    if currency:
        stmt = stmt.where(Booking.currency == currency)

    stmt = stmt.order_by(Booking.end_time.asc())
    result = await session.exec(stmt)
    return list(result.all())


async def create_payout(
    session: AsyncSession,
    owner_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
    admin_id: uuid.UUID,
    currency: str = "USD",
    notes: str | None = None,
) -> Payout:
    bookings = await get_unsettled_bookings(
        session, owner_id, period_start, period_end, currency=currency
    )
    if not bookings:
        raise HTTPException(
            status_code=400, detail="No unsettled bookings found for this period"
        )

    total_amount = sum(b.owner_payout for b in bookings)
    currency = bookings[0].currency

    payout = Payout(
        owner_id=owner_id,
        amount=total_amount,
        currency=currency,
        status="pending",
        period_start=period_start,
        period_end=period_end,
        notes=notes,
    )
    session.add(payout)
    await session.flush()

    for booking in bookings:
        item = PayoutItem(
            payout_id=payout.id,
            booking_id=booking.id,
            booking_total=booking.total_price,
            commission=booking.platform_commission,
            owner_amount=booking.owner_payout,
        )
        session.add(item)

    await session.commit()
    await session.refresh(payout)
    return payout


async def settle_payout(
    session: AsyncSession,
    payout_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> Payout:
    result = await session.exec(
        select(Payout).where(Payout.id == payout_id)
    )
    payout = result.first()
    if payout is None:
        raise HTTPException(status_code=404, detail="Payout not found")
    if payout.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Cannot settle payout in '{payout.status}' state"
        )

    payout.status = "settled"
    payout.settled_at = datetime.now(UTC)
    payout.settled_by = admin_id
    session.add(payout)
    await session.commit()
    await session.refresh(payout)
    return payout


async def list_payouts(
    session: AsyncSession,
    owner_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Payout]:
    stmt = select(Payout)
    if owner_id:
        stmt = stmt.where(Payout.owner_id == owner_id)
    if status_filter:
        stmt = stmt.where(Payout.status == status_filter)
    stmt = stmt.offset(offset).limit(limit).order_by(Payout.created_at.desc())
    result = await session.exec(stmt)
    return list(result.all())


async def get_payout(
    session: AsyncSession,
    payout_id: uuid.UUID,
) -> Payout:
    result = await session.exec(
        select(Payout).where(Payout.id == payout_id)
    )
    payout = result.first()
    if payout is None:
        raise HTTPException(status_code=404, detail="Payout not found")
    return payout


async def get_payout_items(
    session: AsyncSession,
    payout_id: uuid.UUID,
) -> list[PayoutItem]:
    result = await session.exec(
        select(PayoutItem).where(PayoutItem.payout_id == payout_id)
    )
    return list(result.all())
