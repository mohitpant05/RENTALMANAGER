import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import (
    get_current_user,
    get_current_user_with_perms,
    matches_permission,
    require_permission,
)
from app.core.auth.models import User
from app.database import get_db
from app.domains.bookings.schemas import (
    AddAddonRequest,
    BookingCancel,
    BookingCreate,
    BookingGroupResponse,
    BookingReject,
    BookingResponse,
    BundledBookingCreate,
    OnBehalfBookingCreate,
    OnBehalfBookingResponse,
)
from app.domains.bookings.service import (
    add_addon_to_booking,
    cancel_booking,
    confirm_booking,
    create_booking,
    create_booking_on_behalf,
    create_bundled_booking,
    get_booking,
    list_bookings,
    mark_no_show,
    reject_booking,
)

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking_endpoint(
    data: BookingCreate,
    user_and_perms: tuple[User, set[str]] = Depends(get_current_user_with_perms),
    session: AsyncSession = Depends(get_db),
):
    user, perms = user_and_perms
    has_manage = matches_permission("bookings:*:manage", perms)
    return await create_booking(session, data, user.id, is_admin=has_manage)


@router.get("/mine", response_model=list[BookingResponse])
async def list_my_bookings_endpoint(
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    bookings, _ = await list_bookings(
        session,
        user_id=user.id,
        status_filter=status,
        offset=offset,
        limit=limit,
    )
    return bookings


@router.post("/bundled", response_model=BookingGroupResponse, status_code=201)
async def create_bundled_booking_endpoint(
    data: BundledBookingCreate,
    user_and_perms: tuple[User, set[str]] = Depends(get_current_user_with_perms),
    session: AsyncSession = Depends(get_db),
):
    user, perms = user_and_perms
    has_manage = matches_permission("bookings:*:manage", perms)
    primary_data = BookingCreate(
        resource_id=data.primary.resource_id,
        hold_token=data.primary.hold_token,
        start_time=data.primary.start_time,
        end_time=data.primary.end_time,
        notes=data.primary.notes,
        auto_confirm=data.primary.auto_confirm,
        schedules=data.primary.schedules,
    )
    addon_data_list = [
        BookingCreate(
            resource_id=a.resource_id,
            hold_token=a.hold_token,
            start_time=a.start_time,
            end_time=a.end_time,
            notes=a.notes,
            auto_confirm=a.auto_confirm,
            schedules=a.schedules,
        )
        for a in data.addons
    ]
    result = await create_bundled_booking(
        session, primary_data, addon_data_list, user.id,
        is_admin=has_manage,
    )
    return BookingGroupResponse(
        group_id=result["primary"].booking_group_id,
        primary=BookingResponse.model_validate(result["primary"]),
        addons=[BookingResponse.model_validate(a) for a in result["addons"]],
    )


@router.get("", response_model=None)
async def list_bookings_endpoint(
    status: str | None = None,
    resource_id: uuid.UUID | None = None,
    search: str | None = None,
    booking_type: str | None = None,
    offset: int = 0,
    limit: int = 50,
    response: Response = None,
    user_and_perms: tuple[User, set[str]] = Depends(get_current_user_with_perms),
    session: AsyncSession = Depends(get_db),
):
    user, perms = user_and_perms
    can_read_all = matches_permission("bookings:*:read", perms)
    user_filter = None if can_read_all else user.id
    bookings, total = await list_bookings(
        session,
        user_id=user_filter,
        status_filter=status,
        resource_id=resource_id,
        search=search,
        booking_type=booking_type,
        offset=offset,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(bookings)


@router.post("/on-behalf", response_model=OnBehalfBookingResponse, status_code=201)
async def create_on_behalf_endpoint(
    data: OnBehalfBookingCreate,
    user: User = Depends(require_permission("bookings:*:create_on_behalf")),
    session: AsyncSession = Depends(get_db),
):
    booking, created_customer = await create_booking_on_behalf(session, data, user.id)
    return OnBehalfBookingResponse(
        booking=BookingResponse.model_validate(booking),
        created_customer=created_customer,
    )


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking_endpoint(
    booking_id: uuid.UUID,
    user_and_perms: tuple[User, set[str]] = Depends(get_current_user_with_perms),
    session: AsyncSession = Depends(get_db),
):
    user, perms = user_and_perms
    booking = await get_booking(session, booking_id)
    can_read_all = matches_permission("bookings:*:read", perms)
    if not can_read_all and booking.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not the booking owner")
    return booking


@router.post("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking_endpoint(
    booking_id: uuid.UUID,
    user: User = Depends(require_permission("bookings:*:confirm")),
    session: AsyncSession = Depends(get_db),
):
    return await confirm_booking(session, booking_id)


@router.post("/{booking_id}/reject", response_model=BookingResponse)
async def reject_booking_endpoint(
    booking_id: uuid.UUID,
    body: BookingReject | None = None,
    user: User = Depends(require_permission("bookings:*:reject")),
    session: AsyncSession = Depends(get_db),
):
    reason = body.reason if body else None
    return await reject_booking(session, booking_id, reason)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking_endpoint(
    booking_id: uuid.UUID,
    body: BookingCancel | None = None,
    user_and_perms: tuple[User, set[str]] = Depends(get_current_user_with_perms),
    session: AsyncSession = Depends(get_db),
):
    user, perms = user_and_perms
    reason = body.reason if body else None
    has_cancel = matches_permission("bookings:*:cancel", perms)
    return await cancel_booking(session, booking_id, user.id, has_cancel, reason)


@router.post("/{booking_id}/no-show", response_model=BookingResponse)
async def mark_no_show_endpoint(
    booking_id: uuid.UUID,
    user: User = Depends(require_permission("bookings:*:no_show")),
    session: AsyncSession = Depends(get_db),
):
    return await mark_no_show(session, booking_id)


@router.post("/{booking_id}/add-addon", response_model=BookingResponse, status_code=201)
async def add_addon_endpoint(
    booking_id: uuid.UUID,
    data: AddAddonRequest,
    user_and_perms: tuple[User, set[str]] = Depends(get_current_user_with_perms),
    session: AsyncSession = Depends(get_db),
):
    user, perms = user_and_perms
    has_manage = matches_permission("bookings:*:manage", perms)
    return await add_addon_to_booking(
        session, booking_id, data, user.id,
        is_admin=has_manage,
    )
