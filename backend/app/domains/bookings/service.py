import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.email.send import send_email
from app.core.commission.service import calculate_breakdown, resolve_commission
from app.core.email.templates import (
    booking_confirmation_email,
    booking_status_change_email,
)
from app.core.notifications.events import (
    BOOKING_CONFIRMED,
    BOOKING_NEW,
    booking_confirmed_payload,
    booking_new_payload,
)
from app.core.notifications.service import notify as notify_user

logger = logging.getLogger(__name__)

from app.domains.bookings.models import Booking
from app.domains.bookings.schemas import AddAddonRequest, BookingCreate
from app.domains.bookings.state_machine import (
    calculate_refund_percent,
    can_transition,
)
from app.domains.resources.availability.strategy import (
    check_overlap,
    confirm_hold,
    create_hold,
    release_hold,
)
from app.domains.resources.models import Resource, ResourceAvailability, ResourceType
from app.domains.resources.pricing.strategy import get_pricing_provider


async def _dispatch_booking_event(
    session: AsyncSession,
    booking: Booking,
    resource_name: str,
    user_email: str,
    user_name: str,
    event_type: str,
    new_status: str,
):
    try:
        if new_status == "confirmed":
            subject = "Booking Confirmed"
            body = booking_confirmation_email(
                user_name,
                resource_name,
                str(booking.start_time),
                str(booking.end_time),
                f"{booking.currency} {booking.total_price:.2f}",
                booking_id=str(booking.id),
                booking_group_id=str(booking.booking_group_id) if booking.booking_group_id else None,
            )
            send_email(user_email, subject, body)
            await notify_user(
                session, booking.user_id, BOOKING_CONFIRMED, subject, body,
                booking_confirmed_payload(str(booking.id), resource_name),
            )
        elif new_status == "cancelled" or new_status == "rejected":
            subject = f"Booking {new_status.capitalize()}"
            body = booking_status_change_email(user_name, resource_name, new_status)
            send_email(user_email, subject, body)
        elif new_status == "pending":
            subject = "New Booking Pending"
            body = booking_status_change_email(user_name, resource_name, "pending")
            await notify_user(
                session, booking.user_id, BOOKING_NEW, subject, body,
                booking_new_payload(str(booking.id), resource_name, user_name),
            )
    except Exception as e:
        logger.warning("Failed to dispatch booking event: %s", e)


async def create_booking(
    session: AsyncSession,
    data: BookingCreate,
    user_id: uuid.UUID,
    is_admin: bool = False,
    *,
    _from_bundle: bool = False,
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

    booking_user_id = user_id
    if data.user_id is not None:
        if not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Only admins can book on behalf of another user",
            )
        booking_user_id = data.user_id

    bm = getattr(resource_type, "booking_mode", "both") or "both"
    if bm == "bundled" and not _from_bundle:
        raise HTTPException(
            status_code=400,
            detail="This resource type only supports bundled bookings",
        )

    pricing = get_pricing_provider(resource_type.pricing_model)
    total_price = pricing.calculate(
        resource.base_price, data.start_time, data.end_time, resource_type.pricing_config
    )

    if data.schedules:
        if resource_type.pricing_model == "fixed_per_slot":
            total_price = resource.base_price * len(data.schedules)
        elif resource_type.pricing_model == "fixed_per_day":
            total_price = resource.base_price * len(data.schedules)

    commission_config = await resolve_commission(session, data.resource_id)
    breakdown = calculate_breakdown(total_price, resource.currency, commission_config)

    cancellation_policy = resource_type.cancellation_defaults

    schedules_dicts = None
    if data.schedules:
        schedules_dicts = [s.model_dump(mode="json") for s in data.schedules]

    booking = Booking(
        resource_id=data.resource_id,
        user_id=booking_user_id,
        status="pending",
        start_time=data.start_time,
        end_time=data.end_time,
        total_price=total_price,
        currency=resource.currency,
        service_fee=breakdown["service_fee"],
        platform_commission=breakdown["platform_commission"],
        owner_payout=breakdown["owner_payout"],
        customer_total=breakdown["customer_total"],
        hold_token=data.hold_token or None,
        cancellation_policy=cancellation_policy,
        notes=data.notes,
        schedules=schedules_dicts,
        auto_confirm=data.auto_confirm,
        timezone=getattr(data, "timezone", "UTC") or "UTC",
    )

    has_hold = bool(data.hold_token) or bool(data.hold_tokens)

    if has_hold:
        all_tokens = list({t for t in [data.hold_token, *data.hold_tokens] if t})
        for token in all_tokens:
            confirmed = await confirm_hold(session, token, booking.id)
            if not confirmed:
                raise HTTPException(
                    status_code=409,
                    detail="Hold token invalid or expired — please create a new hold",
                )
    else:
        if resource_type.hold_config is not None:
            raise HTTPException(
                status_code=400,
                detail="This resource type requires a hold before booking",
            )
        from sqlmodel import select as sql_select
        await session.exec(
            sql_select(Resource).where(Resource.id == data.resource_id).with_for_update()
        )
        buf = getattr(resource_type, "buffer_minutes", 0) or 0
        available = await check_overlap(
            session, data.resource_id, data.start_time, data.end_time, buf
        )
        if not available:
            raise HTTPException(
                status_code=409,
                detail="Resource is not available for the selected dates",
            )
        avail_record = ResourceAvailability(
            resource_id=data.resource_id,
            start_time=data.start_time,
            end_time=data.end_time,
            status="booked",
            booking_id=booking.id,
        )
        session.add(avail_record)

    if data.auto_confirm:
        booking.status = "confirmed"
        booking.confirmed_at = datetime.now(UTC)

    session.add(booking)
    await session.commit()
    await session.refresh(booking)

    from app.core.auth.models import User
    user_result = await session.exec(select(User).where(User.id == booking_user_id))
    user = user_result.first()
    user_email = user.email if user else ""
    user_name = user.full_name if user else ""

    await _dispatch_booking_event(
        session, booking, resource.name, user_email, user_name,
        "booking.created", booking.status,
    )

    return booking


async def create_booking_on_behalf(
    session: AsyncSession,
    data: "OnBehalfBookingCreate",
    staff_user_id: uuid.UUID,
) -> tuple[Booking, bool]:
    from app.core.auth.models import Role, User, UserRole
    from app.domains.bookings.schemas import OnBehalfBookingCreate

    result = await session.exec(
        select(User).where(User.email == data.customer_email)
    )
    customer = result.first()
    created_customer = False

    if customer is None:
        if not data.customer_name:
            raise HTTPException(
                status_code=400,
                detail="customer_name is required for new customers",
            )
        customer = User(
            email=data.customer_email,
            full_name=data.customer_name,
            phone=data.customer_phone,
            user_type="customer",
            is_active=True,
            is_verified=False,
        )
        session.add(customer)
        await session.flush()

        role_result = await session.exec(
            select(Role).where(Role.slug == "customer")
        )
        customer_role = role_result.first()
        if customer_role:
            session.add(UserRole(user_id=customer.id, role_id=customer_role.id))
            await session.flush()

        created_customer = True

    result = await session.exec(
        select(Resource).where(Resource.id == data.resource_id)
    )
    resource = result.first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    result = await session.exec(
        select(ResourceType).where(ResourceType.id == resource.type_id)
    )
    resource_type = result.first()
    auto_confirm = getattr(resource_type, "staff_booking_auto_confirm", True)

    booking_data = BookingCreate(
        resource_id=data.resource_id,
        hold_token=data.hold_token,
        hold_tokens=data.hold_tokens,
        start_time=data.start_time,
        end_time=data.end_time,
        notes=data.notes,
        auto_confirm=auto_confirm,
        schedules=data.schedules,
    )

    booking = await create_booking(session, booking_data, customer.id, is_admin=True)

    if created_customer:
        try:
            subject = "Welcome — Your Booking Has Been Created"
            body = booking_confirmation_email(
                customer.full_name,
                resource.name,
                str(booking.start_time),
                str(booking.end_time),
                f"{booking.currency} {booking.total_price:.2f}",
                booking_id=str(booking.id),
            )
            send_email(customer.email, subject, body)
        except Exception:
            logger.warning("Failed to send welcome email to %s", customer.email)

    return booking, created_customer


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
    search: str | None = None,
    booking_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[Booking], int]:
    from sqlalchemy import String, cast, func, or_
    from app.core.auth.models import User

    if search:
        condition = or_(
            cast(Booking.id, String).ilike(f"%{search}%"),
            cast(Booking.booking_group_id, String).ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.full_name.ilike(f"%{search}%"),
            Resource.name.ilike(f"%{search}%"),
        )
        base = (
            select(Booking)
            .join(User, Booking.user_id == User.id)
            .join(Resource, Booking.resource_id == Resource.id)
            .where(condition)
        )
        count_base = (
            select(func.count(Booking.id))
            .join(User, Booking.user_id == User.id)
            .join(Resource, Booking.resource_id == Resource.id)
            .where(condition)
        )
    else:
        base = select(Booking)
        count_base = select(func.count(Booking.id))
    if booking_type == "individual":
        base = base.where(Booking.booking_group_id.is_(None))
        count_base = count_base.where(Booking.booking_group_id.is_(None))
    elif booking_type == "bundled":
        base = base.where(Booking.booking_group_id.isnot(None))
        count_base = count_base.where(Booking.booking_group_id.isnot(None))
    if user_id:
        base = base.where(Booking.user_id == user_id)
        count_base = count_base.where(Booking.user_id == user_id)
    if status_filter:
        base = base.where(Booking.status == status_filter)
        count_base = count_base.where(Booking.status == status_filter)
    if resource_id:
        base = base.where(Booking.resource_id == resource_id)
        count_base = count_base.where(Booking.resource_id == resource_id)

    total_row = (await session.exec(count_base)).one()
    total = total_row[0] if isinstance(total_row, (tuple, list)) else total_row

    base = base.offset(offset).limit(limit).order_by(Booking.created_at.desc())
    result = await session.exec(base)
    return list(result.all()), total


async def _load_booking_context(
    session: AsyncSession, booking: Booking
) -> tuple[str, str, str]:
    from app.core.auth.models import User
    user_result = await session.exec(select(User).where(User.id == booking.user_id))
    user = user_result.first()
    resource_result = await session.exec(
        select(Resource).where(Resource.id == booking.resource_id)
    )
    resource = resource_result.first()
    return (
        resource.name if resource else "Resource",
        user.email if user else "",
        user.full_name if user else "Customer",
    )


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

    res_name, user_email, user_name = await _load_booking_context(session, booking)
    await _dispatch_booking_event(
        session, booking, res_name, user_email, user_name,
        "booking.confirmed", "confirmed",
    )
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

    res_name, user_email, user_name = await _load_booking_context(session, booking)
    await _dispatch_booking_event(
        session, booking, res_name, user_email, user_name,
        "booking.rejected", "rejected",
    )
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

    # Cascade cancel: if this is a primary booking, cancel all addons
    if booking.parent_booking_id is None and booking.booking_group_id is not None:
        addon_result = await session.exec(
            select(Booking).where(
                Booking.booking_group_id == booking.booking_group_id,
                Booking.parent_booking_id == booking.id,
                Booking.status.notin_(["cancelled", "completed"]),
            )
        )
        for addon in addon_result.all():
            if can_transition(addon.status, "cancelled"):
                addon.status = "cancelled"
                addon.cancelled_at = datetime.now(UTC)
                addon.cancellation_reason = "Primary booking cancelled"
                addon.refund_percent = 100.0
                addon.updated_at = datetime.now(UTC)
                addon.version += 1
                if addon.hold_token:
                    await release_hold(session, addon.hold_token)
                session.add(addon)
        await session.commit()

    res_name, user_email, user_name = await _load_booking_context(session, booking)
    await _dispatch_booking_event(
        session, booking, res_name, user_email, user_name,
        "booking.cancelled", "cancelled",
    )
    return booking


def _validate_addon_dates(
    primary_start: datetime, primary_end: datetime,
    addon_start: datetime, addon_end: datetime,
) -> None:
    if addon_start < primary_start or addon_end > primary_end:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Addon dates must fall within primary booking range "
                f"({primary_start.isoformat()} to {primary_end.isoformat()})"
            ),
        )


async def create_bundled_booking(
    session: AsyncSession,
    primary_data: BookingCreate,
    addon_data_list: list[BookingCreate],
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> dict:
    group_id = uuid.uuid4()

    result = await session.exec(
        select(Resource).where(Resource.id == primary_data.resource_id)
    )
    primary_resource = result.first()
    if primary_resource:
        rt_result = await session.exec(
            select(ResourceType).where(ResourceType.id == primary_resource.type_id)
        )
        rt = rt_result.first()
        bm = getattr(rt, "booking_mode", "both") or "both"
        if bm == "individual":
            raise HTTPException(
                status_code=400,
                detail="This resource type only supports individual bookings",
            )

    for addon_data in addon_data_list:
        _validate_addon_dates(
            primary_data.start_time, primary_data.end_time,
            addon_data.start_time, addon_data.end_time,
        )

    primary_booking = await create_booking(session, primary_data, user_id, is_admin, _from_bundle=True)
    primary_booking.booking_group_id = group_id
    primary_booking.parent_booking_id = None
    session.add(primary_booking)
    await session.commit()
    await session.refresh(primary_booking)

    addon_bookings = []
    for addon_data in addon_data_list:
        try:
            addon_booking = await create_booking(session, addon_data, user_id, is_admin, _from_bundle=True)
            addon_booking.booking_group_id = group_id
            addon_booking.parent_booking_id = primary_booking.id
            session.add(addon_booking)
            await session.commit()
            await session.refresh(addon_booking)
            addon_bookings.append(addon_booking)
        except HTTPException:
            if addon_data.hold_token:
                await release_hold(session, addon_data.hold_token)
            raise

    return {"primary": primary_booking, "addons": addon_bookings}


async def add_addon_to_booking(
    session: AsyncSession,
    primary_booking_id: uuid.UUID,
    data: AddAddonRequest,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> Booking:
    primary = await get_booking(session, primary_booking_id)
    if primary.parent_booking_id is not None:
        raise HTTPException(status_code=400, detail="Cannot add addon to an addon booking")
    if primary.status not in ("pending", "confirmed"):
        raise HTTPException(status_code=400, detail="Primary booking must be pending or confirmed")

    _validate_addon_dates(
        primary.start_time, primary.end_time,
        data.start_time, data.end_time,
    )

    group_id = primary.booking_group_id or uuid.uuid4()
    if primary.booking_group_id is None:
        primary.booking_group_id = group_id
        session.add(primary)
        await session.commit()

    addon_create = BookingCreate(
        resource_id=data.resource_id,
        hold_token=data.hold_token,
        hold_tokens=data.hold_tokens,
        start_time=data.start_time,
        end_time=data.end_time,
        notes=data.notes,
        auto_confirm=data.auto_confirm,
        schedules=data.schedules,
    )
    addon_booking = await create_booking(session, addon_create, primary.user_id, is_admin, _from_bundle=True)
    addon_booking.booking_group_id = group_id
    addon_booking.parent_booking_id = primary_booking_id
    session.add(addon_booking)
    await session.commit()
    await session.refresh(addon_booking)
    return addon_booking


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
