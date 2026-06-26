import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.models import DemoRequest, DemoRequestStatus
from app.core.admin.platform_auth import get_current_platform_user
from app.core.admin.schemas import (
    DemoRequestCreate,
    DemoRequestResponse,
    DemoRequestStatusUpdate,
    DemoSlotResponse,
)
from app.core.auth.models import PlatformUser
from app.database import get_session
from app.rate_limiter import limiter

router = APIRouter(prefix="/api/demo-requests", tags=["demo-requests"])

SLOT_DURATION_MIN = 30
SLOT_WINDOW_DAYS = 14
BUSINESS_HOUR_START = 9
BUSINESS_HOUR_END = 17


def _generate_meeting_link() -> str:
    code = uuid.uuid4().hex[:12]
    return f"https://meet.rentmanager.com/{code[:3]}-{code[3:7]}-{code[7:]}"


def _generate_slots(from_dt: datetime, days: int) -> list[tuple[datetime, datetime]]:
    slots: list[tuple[datetime, datetime]] = []
    start_date = from_dt.date()
    if from_dt.hour >= BUSINESS_HOUR_END:
        start_date += timedelta(days=1)

    for day_offset in range(days + 14):
        day = start_date + timedelta(days=day_offset)
        if day.weekday() >= 5:
            continue
        for hour in range(BUSINESS_HOUR_START, BUSINESS_HOUR_END):
            for minute in (0, 30):
                slot_start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=UTC)
                slot_end = slot_start + timedelta(minutes=SLOT_DURATION_MIN)
                if slot_start > from_dt:
                    slots.append((slot_start, slot_end))
        if len(slots) >= days * 16:
            break
    return slots[:days * 16]


@router.get("/slots", response_model=list[DemoSlotResponse])
async def list_available_slots(
    session: AsyncSession = Depends(get_session),
):
    now = datetime.now(UTC)
    window_end = now + timedelta(days=SLOT_WINDOW_DAYS)

    booked = await session.exec(
        select(DemoRequest.slot_start).where(
            DemoRequest.slot_start >= now,
            DemoRequest.slot_start <= window_end,
            DemoRequest.status.in_([DemoRequestStatus.pending, DemoRequestStatus.confirmed]),
        )
    )
    booked_starts = {row for row in booked.all()}

    all_slots = _generate_slots(now, SLOT_WINDOW_DAYS)
    available = [
        DemoSlotResponse(start=s, end=e)
        for s, e in all_slots
        if s not in booked_starts
    ]
    return available


@router.get("/calendar", response_model=list[dict])
async def list_calendar_slots(
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    """SuperAdmin view: all slots with booking info for the next 14 days."""
    now = datetime.now(UTC)
    window_end = now + timedelta(days=SLOT_WINDOW_DAYS)

    booked_result = await session.exec(
        select(DemoRequest).where(
            DemoRequest.slot_start >= now,
            DemoRequest.slot_start <= window_end,
            DemoRequest.status.in_([
                DemoRequestStatus.pending,
                DemoRequestStatus.confirmed,
            ]),
        )
    )
    booked_map: dict[datetime, DemoRequest] = {}
    for req in booked_result.all():
        booked_map[req.slot_start] = req

    all_slots = _generate_slots(now, SLOT_WINDOW_DAYS)
    calendar = []
    for s, e in all_slots:
        entry: dict = {"start": s.isoformat(), "end": e.isoformat()}
        if s in booked_map:
            req = booked_map[s]
            entry["status"] = "booked"
            entry["booking"] = DemoRequestResponse.model_validate(req).model_dump(mode="json")
        else:
            entry["status"] = "available"
            entry["booking"] = None
        calendar.append(entry)
    return calendar


@router.post("", response_model=DemoRequestResponse, status_code=201)
@limiter.limit("3/hour")
async def create_demo_request(
    request: Request,
    data: DemoRequestCreate,
    session: AsyncSession = Depends(get_session),
):
    existing = await session.exec(
        select(DemoRequest).where(
            DemoRequest.email == data.email.lower(),
            DemoRequest.status.in_([DemoRequestStatus.pending, DemoRequestStatus.confirmed]),
        )
    )
    if existing.first() is not None:
        raise HTTPException(
            status_code=409,
            detail="You already have an active demo request. Cancel it first to book a new one.",
        )

    now = datetime.now(UTC)
    cooldown = now - timedelta(days=30)
    recent_completed = await session.exec(
        select(DemoRequest).where(
            DemoRequest.email == data.email.lower(),
            DemoRequest.status == DemoRequestStatus.completed,
            DemoRequest.slot_end >= cooldown,
        )
    )
    if recent_completed.first() is not None:
        raise HTTPException(
            status_code=409,
            detail="You had a demo within the last 30 days. Please try again later.",
        )
    if data.slot_start <= now:
        raise HTTPException(status_code=400, detail="Cannot book a slot in the past")

    if data.slot_start.minute not in (0, 30) or data.slot_start.second != 0:
        raise HTTPException(status_code=400, detail="Slot must start on the hour or half-hour")

    if data.slot_start.weekday() >= 5:
        raise HTTPException(status_code=400, detail="Slots only available on weekdays")

    if not (BUSINESS_HOUR_START <= data.slot_start.hour < BUSINESS_HOUR_END):
        raise HTTPException(status_code=400, detail=f"Slots available {BUSINESS_HOUR_START}:00-{BUSINESS_HOUR_END}:00 UTC only")

    slot_taken = await session.exec(
        select(DemoRequest).where(
            DemoRequest.slot_start == data.slot_start,
            DemoRequest.status.in_([DemoRequestStatus.pending, DemoRequestStatus.confirmed]),
        )
    )
    if slot_taken.first() is not None:
        raise HTTPException(status_code=409, detail="This slot is already booked")

    slot_end = data.slot_start + timedelta(minutes=SLOT_DURATION_MIN)
    demo = DemoRequest(
        name=data.name,
        email=data.email.lower(),
        company=data.company,
        message=data.message,
        slot_start=data.slot_start,
        slot_end=slot_end,
    )
    session.add(demo)
    await session.commit()
    await session.refresh(demo)
    return DemoRequestResponse.model_validate(demo)


@router.get("", response_model=list[DemoRequestResponse])
async def list_demo_requests(
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(DemoRequest).order_by(DemoRequest.created_at.desc())
    )
    return [DemoRequestResponse.model_validate(r) for r in result.all()]


@router.patch("/{request_id}/status", response_model=DemoRequestResponse)
async def update_demo_request_status(
    request_id: uuid.UUID,
    data: DemoRequestStatusUpdate,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    try:
        new_status = DemoRequestStatus(data.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {[s.value for s in DemoRequestStatus]}")

    result = await session.exec(
        select(DemoRequest).where(DemoRequest.id == request_id)
    )
    demo = result.first()
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo request not found")

    if new_status == DemoRequestStatus.confirmed and not demo.meeting_link:
        demo.meeting_link = _generate_meeting_link()

    demo.status = new_status
    session.add(demo)
    await session.commit()
    await session.refresh(demo)
    return DemoRequestResponse.model_validate(demo)
