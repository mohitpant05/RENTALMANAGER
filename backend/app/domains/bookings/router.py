import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user, require_permission
from app.core.auth.models import User
from app.database import get_db
from app.domains.bookings.schemas import (
    BookingCancel,
    BookingCreate,
    BookingReject,
    BookingResponse,
)
from app.domains.bookings.service import (
    cancel_booking,
    confirm_booking,
    create_booking,
    get_booking,
    list_bookings,
    mark_no_show,
    reject_booking,
)

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking_endpoint(
    data: BookingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await create_booking(session, data, user.id, is_admin=(user.user_type == "admin"))


@router.get("/mine", response_model=list[BookingResponse])
async def list_my_bookings_endpoint(
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await list_bookings(
        session,
        user_id=user.id,
        status_filter=status,
        offset=offset,
        limit=limit,
    )


@router.get("", response_model=list[BookingResponse])
async def list_bookings_endpoint(
    status: str | None = None,
    resource_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    user_filter = None if user.user_type == "admin" else user.id
    return await list_bookings(
        session,
        user_id=user_filter,
        status_filter=status,
        resource_id=resource_id,
        offset=offset,
        limit=limit,
    )


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking_endpoint(
    booking_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    booking = await get_booking(session, booking_id)
    if user.user_type != "admin" and booking.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not the booking owner")
    return booking


@router.post("/{booking_id}/confirm", response_model=BookingResponse)
async def confirm_booking_endpoint(
    booking_id: uuid.UUID,
    user: User = Depends(require_permission("bookings:*:manage")),
    session: AsyncSession = Depends(get_db),
):
    return await confirm_booking(session, booking_id)


@router.post("/{booking_id}/reject", response_model=BookingResponse)
async def reject_booking_endpoint(
    booking_id: uuid.UUID,
    body: BookingReject | None = None,
    user: User = Depends(require_permission("bookings:*:manage")),
    session: AsyncSession = Depends(get_db),
):
    reason = body.reason if body else None
    return await reject_booking(session, booking_id, reason)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking_endpoint(
    booking_id: uuid.UUID,
    body: BookingCancel | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    reason = body.reason if body else None
    is_admin = user.user_type == "admin"
    return await cancel_booking(session, booking_id, user.id, is_admin, reason)


@router.post("/{booking_id}/no-show", response_model=BookingResponse)
async def mark_no_show_endpoint(
    booking_id: uuid.UUID,
    user: User = Depends(require_permission("bookings:*:manage")),
    session: AsyncSession = Depends(get_db),
):
    return await mark_no_show(session, booking_id)
