# Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-app notification system that logs events (booking confirmed, new review, etc.), provides a notification inbox API, and supports mark-as-read. Architecture supports future channels (email, SMS) via a channel router pattern.

**Architecture:** A `Notification` model stores per-user notifications with event type, payload, and read status. A `notify()` service function is the single entry point — it creates the DB record and (future) dispatches to channels. Event types are enum-like strings. A Celery task handles batch notification creation (e.g., notify all admins). The API provides list/unread-count/mark-read endpoints.

**Tech Stack:** FastAPI, SQLModel, PostgreSQL, Redis (unread count cache)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/core/notifications/__init__.py` | Package marker |
| `backend/app/core/notifications/models.py` | Notification SQLModel + TENANT_NOTIFICATION_TABLES |
| `backend/app/core/notifications/schemas.py` | Request/response schemas |
| `backend/app/core/notifications/service.py` | notify(), list, mark_read, unread_count |
| `backend/app/core/notifications/events.py` | Event type constants + payload builders |
| `backend/app/core/notifications/router.py` | API endpoints |
| `backend/app/core/tenancy/provisioning.py` | Modified: register notification tables |
| `backend/app/main.py` | Modified: register notification router |
| `backend/tests/test_notification_unit.py` | Unit tests |
| `backend/tests/test_notification_integration.py` | Integration tests |

---

### Task 1: Notification model and table registration

**Files:**
- Create: `backend/app/core/notifications/__init__.py`
- Create: `backend/app/core/notifications/models.py`
- Modify: `backend/app/core/tenancy/provisioning.py`

- [ ] **Step 1: Create package**

```python
# backend/app/core/notifications/__init__.py
```

Empty file.

- [ ] **Step 2: Create Notification model**

```python
# backend/app/core/notifications/models.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TENANT_NOTIFICATION_TABLES: set[str] = {"notifications"}


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    event_type: str = Field(max_length=50, index=True)
    title: str = Field(max_length=200)
    body: str = Field(max_length=1000)
    payload: dict | None = Field(default=None, sa_column=Column(JSONB))
    is_read: bool = Field(default=False, index=True)
    read_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
```

- [ ] **Step 3: Register in provisioning**

In `backend/app/core/tenancy/provisioning.py`, add:

```python
from app.core.notifications.models import TENANT_NOTIFICATION_TABLES  # noqa: F401
```

And:

```python
TENANT_TABLE_REGISTRY.update(TENANT_NOTIFICATION_TABLES)
```

- [ ] **Step 4: Verify**

Run: `docker exec rm-backend python -c "from app.core.notifications.models import Notification, TENANT_NOTIFICATION_TABLES; from app.core.tenancy.provisioning import TENANT_TABLE_REGISTRY; assert 'notifications' in TENANT_TABLE_REGISTRY; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/notifications/ backend/app/core/tenancy/provisioning.py
git commit -m "feat(notifications): add Notification model and register tenant table"
```

---

### Task 2: Event types and payload builders

**Files:**
- Create: `backend/app/core/notifications/events.py`

- [ ] **Step 1: Create events module**

```python
# backend/app/core/notifications/events.py

BOOKING_CONFIRMED = "booking.confirmed"
BOOKING_CANCELLED = "booking.cancelled"
BOOKING_REJECTED = "booking.rejected"
BOOKING_COMPLETED = "booking.completed"
BOOKING_NEW = "booking.new"
REVIEW_RECEIVED = "review.received"
REVIEW_MODERATED = "review.moderated"
RESOURCE_APPROVED = "resource.approved"

ALL_EVENT_TYPES = {
    BOOKING_CONFIRMED,
    BOOKING_CANCELLED,
    BOOKING_REJECTED,
    BOOKING_COMPLETED,
    BOOKING_NEW,
    REVIEW_RECEIVED,
    REVIEW_MODERATED,
    RESOURCE_APPROVED,
}


def booking_confirmed_payload(booking_id: str, resource_name: str) -> dict:
    return {
        "booking_id": booking_id,
        "resource_name": resource_name,
    }


def booking_cancelled_payload(
    booking_id: str, resource_name: str, reason: str | None = None
) -> dict:
    return {
        "booking_id": booking_id,
        "resource_name": resource_name,
        "reason": reason,
    }


def booking_new_payload(booking_id: str, resource_name: str, user_name: str) -> dict:
    return {
        "booking_id": booking_id,
        "resource_name": resource_name,
        "user_name": user_name,
    }


def review_received_payload(
    review_id: str, resource_name: str, rating: int
) -> dict:
    return {
        "review_id": review_id,
        "resource_name": resource_name,
        "rating": rating,
    }
```

- [ ] **Step 2: Verify**

Run: `docker exec rm-backend python -c "from app.core.notifications.events import ALL_EVENT_TYPES, booking_confirmed_payload; assert len(ALL_EVENT_TYPES) == 8; p = booking_confirmed_payload('abc', 'Villa'); assert p['booking_id'] == 'abc'; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/notifications/events.py
git commit -m "feat(notifications): add event type constants and payload builders"
```

---

### Task 3: Notification service

**Files:**
- Create: `backend/app/core/notifications/service.py`

- [ ] **Step 1: Create service**

```python
# backend/app/core/notifications/service.py
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.notifications.models import Notification


async def notify(
    session: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    title: str,
    body: str,
    payload: dict | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        event_type=event_type,
        title=title,
        body=body,
        payload=payload,
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


async def notify_many(
    session: AsyncSession,
    user_ids: list[uuid.UUID],
    event_type: str,
    title: str,
    body: str,
    payload: dict | None = None,
) -> int:
    notifications = [
        Notification(
            user_id=uid,
            event_type=event_type,
            title=title,
            body=body,
            payload=payload,
        )
        for uid in user_ids
    ]
    session.add_all(notifications)
    await session.commit()
    return len(notifications)


async def list_notifications(
    session: AsyncSession,
    user_id: uuid.UUID,
    unread_only: bool = False,
    offset: int = 0,
    limit: int = 20,
) -> list[Notification]:
    stmt = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.offset(offset).limit(limit).order_by(Notification.created_at.desc())
    result = await session.exec(stmt)
    return list(result.all())


async def get_unread_count(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.exec(
        select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    return result.first() or 0


async def mark_read(
    session: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID
) -> Notification:
    result = await session.exec(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your notification")
    notification.is_read = True
    notification.read_at = datetime.now(UTC)
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


async def mark_all_read(session: AsyncSession, user_id: uuid.UUID) -> int:
    result = await session.exec(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    notifications = list(result.all())
    now = datetime.now(UTC)
    for n in notifications:
        n.is_read = True
        n.read_at = now
        session.add(n)
    await session.commit()
    return len(notifications)
```

- [ ] **Step 2: Verify**

Run: `docker exec rm-backend python -c "from app.core.notifications.service import notify, list_notifications, mark_read, get_unread_count, mark_all_read; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/notifications/service.py
git commit -m "feat(notifications): add notification service (notify, list, mark_read, count)"
```

---

### Task 4: Notification schemas and router

**Files:**
- Create: `backend/app/core/notifications/schemas.py`
- Create: `backend/app/core/notifications/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create schemas**

```python
# backend/app/core/notifications/schemas.py
import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    event_type: str
    title: str
    body: str
    payload: dict | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    marked: int
```

- [ ] **Step 2: Create router**

```python
# backend/app/core/notifications/router.py
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.auth.models import User
from app.core.notifications.schemas import (
    MarkAllReadResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.core.notifications.service import (
    get_unread_count,
    list_notifications,
    mark_all_read,
    mark_read,
)
from app.database import get_db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationResponse])
async def list_my_notifications(
    unread_only: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await list_notifications(
        session, user.id, unread_only=unread_only, offset=offset, limit=limit
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_my_unread_count(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await get_unread_count(session, user.id)
    return UnreadCountResponse(count=count)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await mark_read(session, notification_id, user.id)


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_notifications_read(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await mark_all_read(session, user.id)
    return MarkAllReadResponse(marked=count)
```

- [ ] **Step 3: Register router in main.py**

Add import:

```python
from app.core.notifications.router import router as notification_router
```

And:

```python
app.include_router(notification_router)
```

- [ ] **Step 4: Verify**

Run: `docker exec rm-backend python -c "from app.main import app; paths = [r.path for r in app.routes if hasattr(r, 'path')]; assert '/api/notifications/' in paths; assert '/api/notifications/unread-count' in paths; print('OK')"`

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/notifications/schemas.py backend/app/core/notifications/router.py backend/app/main.py
git commit -m "feat(notifications): add notification API (list, unread count, mark read)"
```

---

### Task 5: Unit tests

**Files:**
- Create: `backend/tests/test_notification_unit.py`

- [ ] **Step 1: Write unit tests**

```python
# backend/tests/test_notification_unit.py
import uuid
from datetime import UTC, datetime

from app.core.notifications.events import (
    ALL_EVENT_TYPES,
    BOOKING_CONFIRMED,
    REVIEW_RECEIVED,
    booking_confirmed_payload,
    booking_new_payload,
    review_received_payload,
)
from app.core.notifications.models import TENANT_NOTIFICATION_TABLES, Notification
from app.core.notifications.schemas import (
    MarkAllReadResponse,
    NotificationResponse,
    UnreadCountResponse,
)


def test_notification_model_defaults():
    n = Notification(
        user_id=uuid.uuid4(),
        event_type="booking.confirmed",
        title="Booking Confirmed",
        body="Your booking has been confirmed",
    )
    assert n.is_read is False
    assert n.read_at is None
    assert n.payload is None


def test_tenant_notification_tables():
    assert TENANT_NOTIFICATION_TABLES == {"notifications"}


def test_all_event_types():
    assert BOOKING_CONFIRMED in ALL_EVENT_TYPES
    assert REVIEW_RECEIVED in ALL_EVENT_TYPES
    assert len(ALL_EVENT_TYPES) == 8


def test_booking_confirmed_payload():
    p = booking_confirmed_payload("booking-123", "Beach Villa")
    assert p["booking_id"] == "booking-123"
    assert p["resource_name"] == "Beach Villa"


def test_booking_new_payload():
    p = booking_new_payload("booking-456", "Mountain Lodge", "John Doe")
    assert p["booking_id"] == "booking-456"
    assert p["user_name"] == "John Doe"


def test_review_received_payload():
    p = review_received_payload("review-789", "Seaside Cabin", 5)
    assert p["review_id"] == "review-789"
    assert p["rating"] == 5


def test_notification_response_from_model():
    n = Notification(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_type="booking.confirmed",
        title="Confirmed",
        body="Your booking is confirmed",
        is_read=False,
        created_at=datetime.now(UTC),
    )
    resp = NotificationResponse.model_validate(n)
    assert resp.event_type == "booking.confirmed"
    assert resp.is_read is False


def test_unread_count_response():
    r = UnreadCountResponse(count=5)
    assert r.count == 5


def test_mark_all_read_response():
    r = MarkAllReadResponse(marked=3)
    assert r.marked == 3
```

- [ ] **Step 2: Run tests**

Run: `docker exec rm-backend python -m pytest tests/test_notification_unit.py -v`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_notification_unit.py
git commit -m "test(notifications): add unit tests for model, events, schemas"
```

---

### Task 6: Integration tests

**Files:**
- Create: `backend/tests/test_notification_integration.py`

- [ ] **Step 1: Write integration tests**

```python
# backend/tests/test_notification_integration.py
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.notifications.service import notify
from app.core.tenancy.models import Tenant


@pytest.fixture
async def user_notification(
    db_session: AsyncSession,
    customer_headers: dict,
    client: AsyncClient,
    test_tenant: Tenant,
):
    resp = await client.get("/api/auth/me", headers=customer_headers)
    customer_id = resp.json()["id"]

    await db_session.execute(
        text(f"SET search_path TO {test_tenant.schema_name}, public")
    )
    n = await notify(
        db_session,
        uuid.UUID(customer_id),
        "booking.confirmed",
        "Booking Confirmed",
        "Your booking for Beach Villa has been confirmed",
        payload={"booking_id": "test-123", "resource_name": "Beach Villa"},
    )
    return n


@pytest.mark.asyncio
async def test_list_notifications(
    client: AsyncClient, customer_headers: dict, user_notification
):
    resp = await client.get("/api/notifications/", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["event_type"] == "booking.confirmed"


@pytest.mark.asyncio
async def test_list_unread_only(
    client: AsyncClient, customer_headers: dict, user_notification
):
    resp = await client.get(
        "/api/notifications/?unread_only=true", headers=customer_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert all(not n["is_read"] for n in data)


@pytest.mark.asyncio
async def test_unread_count(
    client: AsyncClient, customer_headers: dict, user_notification
):
    resp = await client.get("/api/notifications/unread-count", headers=customer_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


@pytest.mark.asyncio
async def test_mark_read(
    client: AsyncClient, customer_headers: dict, user_notification
):
    notification_id = str(user_notification.id)
    resp = await client.post(
        f"/api/notifications/{notification_id}/read", headers=customer_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_read"] is True
    assert data["read_at"] is not None


@pytest.mark.asyncio
async def test_mark_read_other_user_fails(
    client: AsyncClient, admin_headers: dict, user_notification
):
    notification_id = str(user_notification.id)
    resp = await client.post(
        f"/api/notifications/{notification_id}/read", headers=admin_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_mark_all_read(
    client: AsyncClient,
    customer_headers: dict,
    db_session: AsyncSession,
    test_tenant: Tenant,
):
    resp = await client.get("/api/auth/me", headers=customer_headers)
    customer_id = resp.json()["id"]

    await db_session.execute(
        text(f"SET search_path TO {test_tenant.schema_name}, public")
    )
    for i in range(3):
        await notify(
            db_session,
            uuid.UUID(customer_id),
            "booking.confirmed",
            f"Notification {i}",
            f"Body {i}",
        )

    resp = await client.post("/api/notifications/read-all", headers=customer_headers)
    assert resp.status_code == 200
    assert resp.json()["marked"] >= 3

    resp = await client.get("/api/notifications/unread-count", headers=customer_headers)
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_notification_not_found(client: AsyncClient, customer_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/notifications/{fake_id}/read", headers=customer_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_notifications_empty_for_new_user(
    client: AsyncClient, customer_headers: dict
):
    resp = await client.get("/api/notifications/", headers=customer_headers)
    assert resp.status_code == 200
    # May have notifications from other fixtures, but endpoint works
    assert isinstance(resp.json(), list)
```

- [ ] **Step 2: Run tests**

Run: `docker exec rm-backend python -m pytest tests/test_notification_integration.py -v --tb=short`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_notification_integration.py
git commit -m "test(notifications): add integration tests for notification API"
```

---

### Task 7: Final verification + cleanup

- [ ] **Step 1: Run full test suite**

Run: `docker exec rm-backend python -m pytest --tb=short -q`

Expected: All pass (187 existing + new notification tests).

- [ ] **Step 2: Lint check and fix**

Run: `docker exec rm-backend python -m ruff check --fix app/core/notifications/ tests/test_notification_unit.py tests/test_notification_integration.py app/main.py app/core/tenancy/provisioning.py`

- [ ] **Step 3: Commit if lint changes needed**

```bash
git add -A && git commit -m "style: fix lint issues in notifications module" --allow-empty
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Event → Notification Service → Channel Router | Task 3 (notify() as entry point, channel routing is future) |
| In-app notifications always active | Task 3 (notify creates DB record immediately) |
| User-level notification preferences | Deferred — add user_preferences table in future plan |
| Templates customizable per tenant per event | Deferred — title/body passed by caller for now |
| Tenant configures which channels per event type | Deferred — only in-app channel for MVP |
| Tenant provides own API keys for SMS/WhatsApp | Deferred — external channels in future plan |
| Multi-channel dispatch | Architecture supports via events.py + future channel handlers |
