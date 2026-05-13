# Booking Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a booking engine with state machine, cancellation policies, and Celery-driven lifecycle transitions that consumes the Resource Engine's availability holds.

**Architecture:** Bookings live in the tenant schema alongside resources. A booking is created from an existing availability hold (hold_token), transitions through a state machine (PENDING → CONFIRMED → ACTIVE → COMPLETED), and snapshots the cancellation policy at creation time. Celery beat tasks handle time-based transitions (activate at start_time, complete at end_time) and expired hold cleanup.

**Tech Stack:** FastAPI, SQLModel, Celery + Redis beat, PostgreSQL schema-per-tenant

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/domains/bookings/__init__.py` | Package marker |
| `backend/app/domains/bookings/models.py` | Booking SQLModel + TENANT_BOOKING_TABLES |
| `backend/app/domains/bookings/state_machine.py` | Valid transitions, transition logic, cancellation refund calculator |
| `backend/app/domains/bookings/schemas.py` | Pydantic request/response models |
| `backend/app/domains/bookings/service.py` | Business logic (create, confirm, cancel, etc.) |
| `backend/app/domains/bookings/router.py` | API endpoints |
| `backend/app/domains/bookings/tasks.py` | Celery periodic tasks |
| `backend/app/core/tenancy/provisioning.py` | Modified: add booking tables to registry |
| `backend/app/main.py` | Modified: register booking router |
| `backend/app/celery_app.py` | Modified: add beat schedule |
| `backend/alembic/env.py` | Modified: import booking models |
| `backend/tests/test_booking_unit.py` | State machine + cancellation logic tests |
| `backend/tests/test_booking_integration.py` | Full booking flow via HTTP |

---

### Task 1: Booking model + table registry

**Files:**
- Create: `backend/app/domains/bookings/__init__.py`
- Create: `backend/app/domains/bookings/models.py`
- Modify: `backend/app/core/tenancy/provisioning.py`
- Modify: `backend/alembic/env.py`

- [ ] **Step 1: Create package marker**

```python
# backend/app/domains/bookings/__init__.py
```

Empty file.

- [ ] **Step 2: Create booking model**

```python
# backend/app/domains/bookings/models.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TENANT_BOOKING_TABLES: set[str] = {"bookings"}


class Booking(SQLModel, table=True):
    __tablename__ = "bookings"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", max_length=20, index=True)
    start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    end_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    total_price: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=10)
    hold_token: str | None = Field(default=None, max_length=100)
    cancellation_policy: dict | None = Field(default=None, sa_column=Column(JSONB))
    notes: str | None = Field(default=None, max_length=1000)
    auto_confirm: bool = Field(default=True)
    confirmed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    cancelled_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    cancellation_reason: str | None = Field(default=None, max_length=500)
    refund_percent: float | None = Field(default=None)
    version: int = Field(default=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
```

- [ ] **Step 3: Register booking tables in provisioning**

In `backend/app/core/tenancy/provisioning.py`, add after the existing resource import:

```python
from app.domains.bookings.models import TENANT_BOOKING_TABLES  # noqa: F401
```

And after `TENANT_TABLE_REGISTRY.update(TENANT_RESOURCE_TABLES)`:

```python
TENANT_TABLE_REGISTRY.update(TENANT_BOOKING_TABLES)
```

- [ ] **Step 4: Import booking models in alembic env**

In `backend/alembic/env.py`, add:

```python
from app.domains.bookings.models import Booking  # noqa: F401
```

- [ ] **Step 5: Verify import chain works**

Run: `docker exec rm-backend python -c "from app.domains.bookings.models import Booking, TENANT_BOOKING_TABLES; from app.core.tenancy.provisioning import TENANT_TABLE_REGISTRY; assert 'bookings' in TENANT_TABLE_REGISTRY; print('OK')"`

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/domains/bookings/ backend/app/core/tenancy/provisioning.py backend/alembic/env.py
git commit -m "feat(bookings): add Booking model and register in tenant table registry"
```

---

### Task 2: State machine

**Files:**
- Create: `backend/app/domains/bookings/state_machine.py`

- [ ] **Step 1: Implement state machine**

```python
# backend/app/domains/bookings/state_machine.py
from datetime import UTC, datetime

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "rejected", "cancelled"},
    "confirmed": {"active", "cancelled"},
    "active": {"completed", "cancelled", "no_show"},
}

ALL_STATUSES = {"pending", "confirmed", "rejected", "active", "completed", "cancelled", "no_show"}
TERMINAL_STATUSES = {"rejected", "completed", "cancelled", "no_show"}


def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


def calculate_refund_percent(
    cancellation_policy: dict | None,
    start_time: datetime,
    now: datetime | None = None,
) -> float:
    if cancellation_policy is None:
        return 100.0

    if now is None:
        now = datetime.now(UTC)

    hours_until_start = (start_time - now).total_seconds() / 3600

    free_cancel_hours = cancellation_policy.get("free_cancel_hours", 0)
    partial_cancel_hours = cancellation_policy.get("partial_cancel_hours", 0)
    partial_refund_percent = cancellation_policy.get("partial_refund_percent", 0)
    no_refund_after = cancellation_policy.get("no_refund_after", False)

    if hours_until_start >= free_cancel_hours > 0:
        return 100.0
    if hours_until_start >= partial_cancel_hours > 0:
        return float(partial_refund_percent)
    if no_refund_after:
        return 0.0
    return 100.0
```

- [ ] **Step 2: Verify import**

Run: `docker exec rm-backend python -c "from app.domains.bookings.state_machine import can_transition, calculate_refund_percent, VALID_TRANSITIONS; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/bookings/state_machine.py
git commit -m "feat(bookings): add state machine transitions and cancellation refund calculator"
```

---

### Task 3: Booking schemas

**Files:**
- Create: `backend/app/domains/bookings/schemas.py`

- [ ] **Step 1: Implement schemas**

```python
# backend/app/domains/bookings/schemas.py
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

from app.domains.bookings.state_machine import ALL_STATUSES


class BookingCreate(BaseModel):
    resource_id: uuid.UUID
    hold_token: str
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    auto_confirm: bool = True


class BookingCancel(BaseModel):
    reason: str | None = None


class BookingReject(BaseModel):
    reason: str | None = None


class BookingResponse(BaseModel):
    id: uuid.UUID
    resource_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    start_time: datetime
    end_time: datetime
    total_price: float
    currency: str
    hold_token: str | None
    cancellation_policy: dict | None
    notes: str | None
    auto_confirm: bool
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    refund_percent: float | None
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingListParams(BaseModel):
    status: str | None = None
    resource_id: uuid.UUID | None = None
    offset: int = 0
    limit: int = 50

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ALL_STATUSES:
            raise ValueError(f"Invalid status. Must be one of: {sorted(ALL_STATUSES)}")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("Limit must be between 1 and 100")
        return v
```

- [ ] **Step 2: Verify import**

Run: `docker exec rm-backend python -c "from app.domains.bookings.schemas import BookingCreate, BookingResponse, BookingCancel; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/bookings/schemas.py
git commit -m "feat(bookings): add booking request/response schemas"
```

---

### Task 4: Booking service

**Files:**
- Create: `backend/app/domains/bookings/service.py`

- [ ] **Step 1: Implement booking service**

```python
# backend/app/domains/bookings/service.py
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.bookings.models import Booking
from app.domains.bookings.schemas import BookingCreate
from app.domains.bookings.state_machine import (
    can_transition,
    calculate_refund_percent,
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


async def get_booking(session: AsyncSession, booking_id: uuid.UUID) -> Booking:
    result = await session.exec(
        select(Booking).where(Booking.id == booking_id)
    )
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
    booking = await get_booking(session, booking_id)
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
    booking = await get_booking(session, booking_id)
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
    booking = await get_booking(session, booking_id)

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
    booking = await get_booking(session, booking_id)
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
```

- [ ] **Step 2: Verify import**

Run: `docker exec rm-backend python -c "from app.domains.bookings.service import create_booking, confirm_booking, cancel_booking; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/bookings/service.py
git commit -m "feat(bookings): add booking service with create, confirm, cancel, reject, no-show"
```

---

### Task 5: Booking router + main.py registration

**Files:**
- Create: `backend/app/domains/bookings/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Implement booking router**

```python
# backend/app/domains/bookings/router.py
import uuid

from fastapi import APIRouter, Depends
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
    return await create_booking(session, data, user.id)


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
        from fastapi import HTTPException
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
```

- [ ] **Step 2: Register router in main.py**

In `backend/app/main.py`, add import:

```python
from app.domains.bookings.router import router as booking_router
```

And add after `app.include_router(resource_router)`:

```python
app.include_router(booking_router)
```

- [ ] **Step 3: Verify server starts**

Run: `docker exec rm-backend python -c "from app.main import app; print([r.path for r in app.routes if hasattr(r, 'path') and 'booking' in r.path])"`

Expected: List containing booking paths like `/api/bookings`, `/api/bookings/{booking_id}`, etc.

- [ ] **Step 4: Commit**

```bash
git add backend/app/domains/bookings/router.py backend/app/main.py
git commit -m "feat(bookings): add booking API router with CRUD and state transition endpoints"
```

---

### Task 6: Celery tasks (hold cleanup + state transitions)

**Files:**
- Create: `backend/app/domains/bookings/tasks.py`
- Modify: `backend/app/celery_app.py`

- [ ] **Step 1: Implement Celery tasks**

```python
# backend/app/domains/bookings/tasks.py
from datetime import UTC, datetime

from sqlalchemy import text
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
```

- [ ] **Step 2: Create synchronous Celery task wrappers in celery_app.py**

Replace `backend/app/celery_app.py` with:

```python
import asyncio

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "rentmanager",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _run_for_all_tenants(task_fn):
    from sqlmodel import select
    from app.database import async_session_factory
    from app.core.tenancy.models import Tenant

    async with async_session_factory() as session:
        result = await session.exec(
            select(Tenant).where(Tenant.is_active.is_(True))
        )
        tenants = list(result.all())

    total = 0
    for tenant in tenants:
        from sqlalchemy import text as sa_text
        async with async_session_factory() as session:
            await session.execute(
                sa_text(f"SET search_path TO {tenant.schema_name}, public")
            )
            count = await task_fn(session)
            total += count
            await session.execute(sa_text("SET search_path TO public"))
    return total


@celery.task(name="bookings.cleanup_expired_holds")
def task_cleanup_expired_holds():
    from app.domains.bookings.tasks import cleanup_expired_holds
    return _run_async(_run_for_all_tenants(cleanup_expired_holds))


@celery.task(name="bookings.activate_confirmed")
def task_activate_confirmed():
    from app.domains.bookings.tasks import activate_confirmed_bookings
    return _run_async(_run_for_all_tenants(activate_confirmed_bookings))


@celery.task(name="bookings.complete_active")
def task_complete_active():
    from app.domains.bookings.tasks import complete_active_bookings
    return _run_async(_run_for_all_tenants(complete_active_bookings))


celery.conf.beat_schedule = {
    "cleanup-expired-holds": {
        "task": "bookings.cleanup_expired_holds",
        "schedule": 60.0,
    },
    "activate-confirmed-bookings": {
        "task": "bookings.activate_confirmed",
        "schedule": 60.0,
    },
    "complete-active-bookings": {
        "task": "bookings.complete_active",
        "schedule": 60.0,
    },
}
```

- [ ] **Step 3: Verify imports**

Run: `docker exec rm-backend python -c "from app.domains.bookings.tasks import cleanup_expired_holds, activate_confirmed_bookings, complete_active_bookings; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/domains/bookings/tasks.py backend/app/celery_app.py
git commit -m "feat(bookings): add Celery tasks for hold cleanup and booking lifecycle transitions"
```

---

### Task 7: Unit tests

**Files:**
- Create: `backend/tests/test_booking_unit.py`

- [ ] **Step 1: Write unit tests**

```python
# backend/tests/test_booking_unit.py
from datetime import UTC, datetime, timedelta

from app.domains.bookings.state_machine import (
    ALL_STATUSES,
    TERMINAL_STATUSES,
    VALID_TRANSITIONS,
    calculate_refund_percent,
    can_transition,
)


def test_can_transition_pending_to_confirmed():
    assert can_transition("pending", "confirmed") is True


def test_can_transition_pending_to_rejected():
    assert can_transition("pending", "rejected") is True


def test_can_transition_pending_to_cancelled():
    assert can_transition("pending", "cancelled") is True


def test_cannot_transition_pending_to_active():
    assert can_transition("pending", "active") is False


def test_can_transition_confirmed_to_active():
    assert can_transition("confirmed", "active") is True


def test_can_transition_confirmed_to_cancelled():
    assert can_transition("confirmed", "cancelled") is True


def test_cannot_transition_confirmed_to_rejected():
    assert can_transition("confirmed", "rejected") is False


def test_can_transition_active_to_completed():
    assert can_transition("active", "completed") is True


def test_can_transition_active_to_no_show():
    assert can_transition("active", "no_show") is True


def test_can_transition_active_to_cancelled():
    assert can_transition("active", "cancelled") is True


def test_cannot_transition_from_terminal_states():
    for terminal in TERMINAL_STATUSES:
        for target in ALL_STATUSES:
            assert can_transition(terminal, target) is False


def test_all_statuses_complete():
    assert ALL_STATUSES == {
        "pending", "confirmed", "rejected", "active",
        "completed", "cancelled", "no_show",
    }


def test_terminal_statuses():
    assert TERMINAL_STATUSES == {"rejected", "completed", "cancelled", "no_show"}


def test_refund_full_when_no_policy():
    start = datetime.now(UTC) + timedelta(hours=100)
    assert calculate_refund_percent(None, start) == 100.0


def test_refund_full_within_free_cancel_window():
    policy = {"free_cancel_hours": 48, "partial_cancel_hours": 24, "partial_refund_percent": 50, "no_refund_after": True}
    now = datetime.now(UTC)
    start = now + timedelta(hours=72)
    assert calculate_refund_percent(policy, start, now=now) == 100.0


def test_refund_partial_within_partial_window():
    policy = {"free_cancel_hours": 48, "partial_cancel_hours": 24, "partial_refund_percent": 50, "no_refund_after": True}
    now = datetime.now(UTC)
    start = now + timedelta(hours=30)
    assert calculate_refund_percent(policy, start, now=now) == 50.0


def test_refund_zero_past_all_windows():
    policy = {"free_cancel_hours": 48, "partial_cancel_hours": 24, "partial_refund_percent": 50, "no_refund_after": True}
    now = datetime.now(UTC)
    start = now + timedelta(hours=10)
    assert calculate_refund_percent(policy, start, now=now) == 0.0


def test_refund_full_when_no_refund_after_false():
    policy = {"free_cancel_hours": 48, "partial_cancel_hours": 0, "no_refund_after": False}
    now = datetime.now(UTC)
    start = now + timedelta(hours=10)
    assert calculate_refund_percent(policy, start, now=now) == 100.0


def test_refund_exactly_at_free_cancel_boundary():
    policy = {"free_cancel_hours": 48, "partial_cancel_hours": 24, "partial_refund_percent": 50, "no_refund_after": True}
    now = datetime.now(UTC)
    start = now + timedelta(hours=48)
    assert calculate_refund_percent(policy, start, now=now) == 100.0


def test_refund_just_below_free_cancel_boundary():
    policy = {"free_cancel_hours": 48, "partial_cancel_hours": 24, "partial_refund_percent": 50, "no_refund_after": True}
    now = datetime.now(UTC)
    start = now + timedelta(hours=47, minutes=59)
    assert calculate_refund_percent(policy, start, now=now) == 50.0


# --- Model tests ---

import uuid

from app.domains.bookings.models import Booking, TENANT_BOOKING_TABLES


def test_booking_model_defaults():
    b = Booking(
        resource_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(days=1),
        total_price=100.0,
    )
    assert b.status == "pending"
    assert b.currency == "USD"
    assert b.version == 1
    assert b.auto_confirm is True
    assert b.hold_token is None


def test_tenant_booking_tables():
    assert TENANT_BOOKING_TABLES == {"bookings"}


# --- Schema tests ---

from pydantic import ValidationError

from app.domains.bookings.schemas import BookingCreate, BookingListParams


def test_booking_create_schema_valid():
    data = BookingCreate(
        resource_id=uuid.uuid4(),
        hold_token="tok-123",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(days=1),
    )
    assert data.auto_confirm is True
    assert data.notes is None


def test_booking_list_params_invalid_status():
    try:
        BookingListParams(status="invalid_status")
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_booking_list_params_limit_bounds():
    try:
        BookingListParams(limit=0)
        assert False, "Should have raised"
    except ValidationError:
        pass

    try:
        BookingListParams(limit=101)
        assert False, "Should have raised"
    except ValidationError:
        pass
```

- [ ] **Step 2: Run unit tests**

Run: `docker exec rm-backend python -m pytest tests/test_booking_unit.py -v`

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_booking_unit.py
git commit -m "test(bookings): add unit tests for state machine, cancellation, model, schemas"
```

---

### Task 8: Integration tests

**Files:**
- Create: `backend/tests/test_booking_integration.py`

- [ ] **Step 1: Write integration tests**

```python
# backend/tests/test_booking_integration.py
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.fixture
async def venue_type(client: AsyncClient, admin_headers: dict) -> dict:
    resp = await client.post(
        "/api/resource-types",
        json={
            "name": "Booking Test Venues",
            "slug": "booking-test-venues",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
            "cancellation_defaults": {
                "free_cancel_hours": 48,
                "partial_cancel_hours": 24,
                "partial_refund_percent": 50,
                "no_refund_after": True,
            },
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def active_resource(
    client: AsyncClient, admin_headers: dict, venue_type: dict
) -> dict:
    resp = await client.post(
        "/api/resources",
        json={
            "type_id": venue_type["id"],
            "name": "Booking Test Apartment",
            "base_price": 100.0,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    resource = resp.json()

    resp = await client.patch(
        f"/api/resources/{resource['id']}",
        json={"status": "active"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture
async def held_resource(
    client: AsyncClient, admin_headers: dict, active_resource: dict
) -> dict:
    now = datetime.now(UTC)
    start = (now + timedelta(days=5)).isoformat()
    end = (now + timedelta(days=8)).isoformat()

    resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    hold_data = resp.json()
    return {
        "resource_id": active_resource["id"],
        "hold_token": hold_data["hold_token"],
        "start_time": start,
        "end_time": end,
    }


# --- Booking creation ---


@pytest.mark.anyio
async def test_create_booking_auto_confirm(
    client: AsyncClient, admin_headers: dict, held_resource: dict
):
    resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": held_resource["resource_id"],
            "hold_token": held_resource["hold_token"],
            "start_time": held_resource["start_time"],
            "end_time": held_resource["end_time"],
            "auto_confirm": True,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    booking = resp.json()
    assert booking["status"] == "confirmed"
    assert booking["confirmed_at"] is not None
    assert booking["total_price"] == 300.0  # 3 days * $100


@pytest.mark.anyio
async def test_create_booking_manual_confirm(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=15)).isoformat()
    end = (now + timedelta(days=17)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    assert hold_resp.status_code == 200
    hold_token = hold_resp.json()["hold_token"]

    resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": False,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    booking = resp.json()
    assert booking["status"] == "pending"
    assert booking["confirmed_at"] is None


@pytest.mark.anyio
async def test_create_booking_invalid_hold_token(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=20)).isoformat()
    end = (now + timedelta(days=22)).isoformat()

    resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": "invalid-token-does-not-exist",
            "start_time": start,
            "end_time": end,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert "hold" in resp.json()["detail"].lower()


# --- Booking state transitions ---


@pytest.mark.anyio
async def test_confirm_pending_booking(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=25)).isoformat()
    end = (now + timedelta(days=27)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": False,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/confirm",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"


@pytest.mark.anyio
async def test_reject_pending_booking(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=30)).isoformat()
    end = (now + timedelta(days=32)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": False,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/reject",
        json={"reason": "Not available"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["cancellation_reason"] == "Not available"


@pytest.mark.anyio
async def test_cancel_booking_with_full_refund(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=35)).isoformat()
    end = (now + timedelta(days=37)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": True,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/cancel",
        json={"reason": "Changed plans"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["refund_percent"] == 100.0
    assert data["cancellation_reason"] == "Changed plans"


@pytest.mark.anyio
async def test_cancel_booking_no_refund(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    # Start in 10 hours — past both free (48h) and partial (24h) windows
    start = (now + timedelta(hours=10)).isoformat()
    end = (now + timedelta(hours=34)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": True,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/cancel",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["refund_percent"] == 0.0


@pytest.mark.anyio
async def test_cannot_confirm_already_confirmed(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=40)).isoformat()
    end = (now + timedelta(days=42)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": True,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/confirm",
        headers=admin_headers,
    )
    assert resp.status_code == 409


# --- List and get ---


@pytest.mark.anyio
async def test_list_bookings(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=45)).isoformat()
    end = (now + timedelta(days=47)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
        },
        headers=admin_headers,
    )

    resp = await client.get("/api/bookings", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.anyio
async def test_get_booking_by_id(
    client: AsyncClient, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=50)).isoformat()
    end = (now + timedelta(days=52)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/bookings/{booking_id}", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == booking_id


# --- Customer access ---


@pytest.mark.anyio
async def test_customer_cannot_confirm_booking(
    client: AsyncClient, customer_headers: dict, admin_headers: dict, active_resource: dict
):
    now = datetime.now(UTC)
    start = (now + timedelta(days=55)).isoformat()
    end = (now + timedelta(days=57)).isoformat()

    hold_resp = await client.post(
        f"/api/resources/{active_resource['id']}/availability/hold",
        json={"start_time": start, "end_time": end},
        headers=admin_headers,
    )
    hold_token = hold_resp.json()["hold_token"]

    create_resp = await client.post(
        "/api/bookings",
        json={
            "resource_id": active_resource["id"],
            "hold_token": hold_token,
            "start_time": start,
            "end_time": end,
            "auto_confirm": False,
        },
        headers=admin_headers,
    )
    booking_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/bookings/{booking_id}/confirm",
        headers=customer_headers,
    )
    assert resp.status_code == 403


# --- Celery task unit tests ---


@pytest.mark.anyio
async def test_cleanup_expired_holds(db_session, test_tenant, db_engine):
    from datetime import UTC, datetime, timedelta
    import uuid
    from sqlalchemy import text
    from app.domains.resources.models import ResourceAvailability, ResourceType, Resource
    from app.domains.bookings.tasks import cleanup_expired_holds

    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    rt = ResourceType(
        name="Task Test", slug="task-test-rt",
        availability_model="date_range", pricing_model="fixed_per_day",
    )
    db_session.add(rt)
    await db_session.commit()
    await db_session.refresh(rt)

    resource = Resource(
        type_id=rt.id, name="Task Test Res",
        base_price=50.0, owner_id=uuid.uuid4(), status="active",
    )
    db_session.add(resource)
    await db_session.commit()
    await db_session.refresh(resource)

    expired_hold = ResourceAvailability(
        resource_id=resource.id,
        start_time=datetime.now(UTC) + timedelta(days=1),
        end_time=datetime.now(UTC) + timedelta(days=2),
        status="held",
        hold_token="expired-token",
        hold_expires=datetime.now(UTC) - timedelta(minutes=5),
    )
    db_session.add(expired_hold)
    await db_session.commit()

    count = await cleanup_expired_holds(db_session)
    assert count == 1

    await db_session.execute(text("SET search_path TO public"))
```

- [ ] **Step 2: Run integration tests**

Run: `docker exec rm-backend python -m pytest tests/test_booking_integration.py -v`

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_booking_integration.py
git commit -m "test(bookings): add integration tests for booking flow, state transitions, RBAC"
```

---

### Task 9: Final verification + cleanup

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

Run: `docker exec rm-backend python -m pytest --tb=short -q`

Expected: All tests pass (107 existing + new booking tests).

- [ ] **Step 2: Lint check**

Run: `docker exec rm-backend python -m ruff check app/domains/bookings/ tests/test_booking_unit.py tests/test_booking_integration.py`

Expected: All checks passed (or only pre-existing issues).

- [ ] **Step 3: Verify table registry**

Run: `docker exec rm-backend python -c "from app.core.tenancy.provisioning import TENANT_TABLE_REGISTRY; assert 'bookings' in TENANT_TABLE_REGISTRY; print('OK:', sorted(TENANT_TABLE_REGISTRY))"`

Expected: `OK: ['bookings', 'permissions', 'resource_availability', 'resource_types', 'resources', 'role_permissions', 'roles', 'user_roles', 'users']`

- [ ] **Step 4: Verify API routes registered**

Run: `docker exec rm-backend python -c "from app.main import app; paths = [r.path for r in app.routes if hasattr(r, 'path')]; assert '/api/bookings' in paths; print('Booking routes:', [p for p in paths if 'booking' in p])"`

Expected: Shows all booking paths.

- [ ] **Step 5: Fix any lint issues and commit**

```bash
docker exec rm-backend python -m ruff check --fix app/domains/bookings/ tests/test_booking_unit.py tests/test_booking_integration.py
git add -A
git commit -m "style: fix lint issues in booking engine" --allow-empty
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| State machine (DRAFT→PENDING→CONFIRMED→ACTIVE→COMPLETED + REJECTED/CANCELLED/NO_SHOW) | Task 2 (state_machine.py). Note: DRAFT omitted for MVP since no payment step exists — bookings start as PENDING. |
| Cancellation policy (admin-configurable, snapshotted) | Task 2 (calculate_refund_percent) + Task 4 (snapshot at creation) |
| Hold confirmation (converts hold → booked) | Task 4 (create_booking calls confirm_hold) |
| Auto-confirm or manual confirm | Task 4 (auto_confirm flag) |
| Celery hold expiry cleanup | Task 6 (cleanup_expired_holds) |
| Celery state transitions (CONFIRMED→ACTIVE, ACTIVE→COMPLETED) | Task 6 (activate/complete tasks) |
| RBAC on admin actions (confirm/reject/no-show) | Task 5 (require_permission) |
| Owner-only cancel | Task 4 (cancel_booking checks user_id) |
| Version column / optimistic locking | Task 1 (model has version), Task 4 (increments on transition) |
| MVP: no payment processing | Correct — no payment fields |
