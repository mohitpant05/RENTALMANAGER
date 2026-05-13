# Service Discovery & Bundled Booking — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the resource engine with type roles (primary/addon/standalone/hidden), manual resource assignment, geo-radius addon discovery, bundled booking (primary + add-ons), staff support manager capability, and a venue-first public page redesign.

**Architecture:** Add `role` and `discovery_radius_km` to `ResourceType`, create `ResourceAssignment` join table, add `parent_booking_id` and `booking_group_id` to `Booking`, add `support_contact_id` to `Resource`. New addon discovery endpoint uses Haversine geo query. Bundled booking endpoint atomically holds all resources and creates linked bookings. Frontend shows primary types on landing page, addon resources on venue detail during checkout.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, PostgreSQL Haversine | Next.js 15, React 19, TypeScript, Zustand, TanStack Query, Zod, shadcn/ui

---

## Pre-Implementation Notes

**What already exists (do NOT recreate):**
- `ResourceType` model with all CRUD in `backend/app/domains/resources/models.py`
- `Resource` model with `location_lat`, `location_lng` fields (geo-ready)
- `ResourceAvailability` with hold/release/confirm in `backend/app/domains/resources/availability/strategy.py`
- `Booking` model with state machine in `backend/app/domains/bookings/`
- `create_booking` service in `backend/app/domains/bookings/service.py`
- `check_overlap`, `create_hold`, `confirm_hold`, `release_hold` in `backend/app/domains/resources/availability/strategy.py`
- Frontend resource detail page at `frontend/src/app/(public)/resources/[id]/page.tsx`
- Frontend booking flow hook at `frontend/src/hooks/use-booking-flow.ts`
- Frontend home page at `frontend/src/app/page.tsx`
- `TENANT_RESOURCE_TABLES` set in `backend/app/domains/resources/models.py`
- `TENANT_BOOKING_TABLES` set in `backend/app/domains/bookings/models.py`
- Permission check `require_permission("resources:*:manage")` in auth dependencies
- `VALID_RESOURCE_STATUSES`, `ResourceTypeCreate/Update/Response`, `ResourceCreate/Update/Response` schemas

**File Structure:**

```
backend/app/
├── domains/
│   ├── resources/
│   │   ├── models.py                      # MODIFY: add role, discovery_radius_km to ResourceType; support_contact_id to Resource; ResourceAssignment model
│   │   ├── schemas.py                     # MODIFY: add role/radius to type schemas; add assignment schemas; add addon discovery response
│   │   ├── service.py                     # MODIFY: add assignment CRUD, addon discovery
│   │   ├── router.py                      # MODIFY: add assignment endpoints, addon discovery endpoint
│   │   └── discovery.py                   # CREATE: addon discovery algorithm (Haversine + assignment merge)
│   ├── bookings/
│   │   ├── models.py                      # MODIFY: add parent_booking_id, booking_group_id
│   │   ├── schemas.py                     # MODIFY: add BundledBookingCreate, AddAddonRequest
│   │   ├── service.py                     # MODIFY: add create_bundled_booking, add_addon_to_booking, cascade cancel
│   │   └── router.py                      # MODIFY: add bundled booking endpoint, add-addon endpoint
├── core/
│   └── auth/
│       └── seed.py                        # MODIFY: add resources:*:assign_for_customer permission

backend/tests/
├── test_discovery_unit.py                 # CREATE
├── test_bundled_booking_integration.py    # CREATE

frontend/src/
├── hooks/
│   ├── use-booking-flow.ts                # MODIFY: support multi-resource holds
│   └── use-addons.ts                      # CREATE: addon discovery + assignment hooks
├── components/
│   └── public/
│       ├── addon-discovery-section.tsx     # CREATE
│       ├── addon-resource-card.tsx         # CREATE
│       ├── bundled-checkout.tsx            # CREATE
│       └── support-contact-card.tsx        # CREATE
├── app/
│   ├── page.tsx                           # MODIFY: show only primary types
│   └── (public)/resources/[id]/page.tsx   # MODIFY: add addon section + support contact
├── types/
│   └── api.ts                             # MODIFY: add addon/assignment/bundled types
```

---

### Task 1: Add Role & Radius to ResourceType Model

**Files:**
- Modify: `backend/app/domains/resources/models.py`
- Modify: `backend/app/domains/resources/schemas.py`

- [ ] **Step 1: Add fields to ResourceType model**

In `backend/app/domains/resources/models.py`, add these fields to `ResourceType` class after `commission_config`:

```python
    role: str = Field(default="standalone", max_length=20)
    discovery_radius_km: float | None = Field(default=None)
    display_order: int = Field(default=0)
```

- [ ] **Step 2: Add role validation to schemas**

In `backend/app/domains/resources/schemas.py`, add constant:

```python
VALID_RESOURCE_TYPE_ROLES = {"primary", "addon", "standalone", "hidden"}
```

Add to `ResourceTypeCreate` class (after `requires_verification`):

```python
    role: str = "standalone"
    discovery_radius_km: float | None = None
    display_order: int = 0

    @field_validator("role")
    @classmethod
    def check_role(cls, v: str) -> str:
        if v not in VALID_RESOURCE_TYPE_ROLES:
            raise ValueError(f"Must be one of {VALID_RESOURCE_TYPE_ROLES}")
        return v
```

Add to `ResourceTypeUpdate` class:

```python
    role: str | None = None
    discovery_radius_km: float | None = None
    display_order: int | None = None
```

Add to `ResourceTypeResponse` class (after `requires_verification`):

```python
    role: str
    discovery_radius_km: float | None
    display_order: int
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/resources/models.py backend/app/domains/resources/schemas.py
git commit -m "feat(resources): add role, discovery_radius_km, display_order to ResourceType"
```

---

### Task 2: Add support_contact_id to Resource Model

**Files:**
- Modify: `backend/app/domains/resources/models.py`
- Modify: `backend/app/domains/resources/schemas.py`

- [ ] **Step 1: Add field to Resource model**

In `backend/app/domains/resources/models.py`, add to `Resource` class after `suspension_reason`:

```python
    support_contact_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
```

- [ ] **Step 2: Add to schemas**

In `backend/app/domains/resources/schemas.py`, add to `ResourceCreate`:

```python
    support_contact_id: uuid.UUID | None = None
```

Add to `ResourceUpdate`:

```python
    support_contact_id: uuid.UUID | None = None
```

Add to `ResourceResponse`:

```python
    support_contact_id: uuid.UUID | None
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/resources/models.py backend/app/domains/resources/schemas.py
git commit -m "feat(resources): add support_contact_id to Resource"
```

---

### Task 3: Create ResourceAssignment Model

**Files:**
- Modify: `backend/app/domains/resources/models.py`
- Modify: `backend/app/domains/resources/schemas.py`

- [ ] **Step 1: Add ResourceAssignment model**

In `backend/app/domains/resources/models.py`, add after the `ResourceAvailability` class:

```python
class ResourceAssignment(SQLModel, table=True):
    __tablename__ = "resource_assignments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    primary_resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    addon_resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    priority: int = Field(default=0)
    assigned_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
```

Update `TENANT_RESOURCE_TABLES` to include the new table:

```python
TENANT_RESOURCE_TABLES: set[str] = {
    "resource_types",
    "resources",
    "resource_availability",
    "resource_assignments",
}
```

- [ ] **Step 2: Add assignment schemas**

In `backend/app/domains/resources/schemas.py`, add:

```python
class ResourceAssignmentCreate(BaseModel):
    addon_resource_id: uuid.UUID
    priority: int = 0


class ResourceAssignmentUpdate(BaseModel):
    priority: int


class ResourceAssignmentResponse(BaseModel):
    id: uuid.UUID
    primary_resource_id: uuid.UUID
    addon_resource_id: uuid.UUID
    priority: int
    assigned_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/resources/models.py backend/app/domains/resources/schemas.py
git commit -m "feat(resources): add ResourceAssignment model and schemas"
```

---

### Task 4: Add Booking Group Fields

**Files:**
- Modify: `backend/app/domains/bookings/models.py`
- Modify: `backend/app/domains/bookings/schemas.py`

- [ ] **Step 1: Add fields to Booking model**

In `backend/app/domains/bookings/models.py`, add to `Booking` class after `auto_confirm`:

```python
    parent_booking_id: uuid.UUID | None = Field(default=None, foreign_key="bookings.id", index=True)
    booking_group_id: uuid.UUID | None = Field(default=None, index=True)
```

- [ ] **Step 2: Add to BookingResponse schema**

In `backend/app/domains/bookings/schemas.py`, add to `BookingResponse` after `auto_confirm`:

```python
    parent_booking_id: uuid.UUID | None
    booking_group_id: uuid.UUID | None
```

- [ ] **Step 3: Add BundledBookingCreate and AddAddonRequest schemas**

In `backend/app/domains/bookings/schemas.py`, add:

```python
class BookingItemCreate(BaseModel):
    resource_id: uuid.UUID
    hold_token: str
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    auto_confirm: bool = True


class BundledBookingCreate(BaseModel):
    primary: BookingItemCreate
    addons: list[BookingItemCreate] = []


class AddAddonRequest(BaseModel):
    resource_id: uuid.UUID
    hold_token: str
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    auto_confirm: bool = True


class BookingGroupResponse(BaseModel):
    group_id: uuid.UUID
    primary: BookingResponse
    addons: list[BookingResponse]
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/domains/bookings/models.py backend/app/domains/bookings/schemas.py
git commit -m "feat(bookings): add parent_booking_id, booking_group_id, bundled booking schemas"
```

---

### Task 5: Implement Addon Discovery Service

**Files:**
- Create: `backend/app/domains/resources/discovery.py`
- Create: `backend/tests/test_discovery_unit.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_discovery_unit.py`:

```python
import math
import pytest

from app.domains.resources.discovery import haversine_distance_km


def test_haversine_same_point():
    assert haversine_distance_km(30.0, 78.0, 30.0, 78.0) == 0.0


def test_haversine_known_distance():
    # Delhi (28.6139, 77.2090) to Rishikesh (30.0869, 78.2676)
    d = haversine_distance_km(28.6139, 77.2090, 30.0869, 78.2676)
    assert 180 < d < 200  # ~190 km


def test_haversine_short_distance():
    # Two points ~1 km apart
    d = haversine_distance_km(30.0, 78.0, 30.009, 78.0)
    assert 0.9 < d < 1.1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_discovery_unit.py -v`
Expected: FAIL — `ImportError: cannot import name 'haversine_distance_km'`

- [ ] **Step 3: Implement discovery module**

Create `backend/app/domains/resources/discovery.py`:

```python
import math
import uuid

from sqlalchemy import text
from sqlmodel import and_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.availability.strategy import check_overlap
from app.domains.resources.models import Resource, ResourceAssignment, ResourceType


def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def discover_addons(
    session: AsyncSession,
    venue_id: uuid.UUID,
    start: "datetime",
    end: "datetime",
) -> dict[str, dict]:
    from datetime import datetime

    venue_result = await session.exec(
        select(Resource).where(Resource.id == venue_id)
    )
    venue = venue_result.first()
    if venue is None:
        return {}

    addon_types_result = await session.exec(
        select(ResourceType).where(
            ResourceType.role == "addon",
            ResourceType.is_active.is_(True),
        )
    )
    addon_types = list(addon_types_result.all())
    if not addon_types:
        return {}

    assigned_result = await session.exec(
        select(ResourceAssignment).where(
            ResourceAssignment.primary_resource_id == venue_id
        ).order_by(ResourceAssignment.priority)
    )
    assignments = list(assigned_result.all())
    assigned_addon_ids = {a.addon_resource_id for a in assignments}

    result: dict[str, list[dict]] = {}

    for addon_type in addon_types:
        items: list[dict] = []
        assigned_ids_for_type: set[uuid.UUID] = set()

        # 1. Manually assigned resources of this type
        for assignment in assignments:
            res_result = await session.exec(
                select(Resource).where(
                    Resource.id == assignment.addon_resource_id,
                    Resource.type_id == addon_type.id,
                    Resource.status == "active",
                )
            )
            resource = res_result.first()
            if resource is None:
                continue

            available = await check_overlap(session, resource.id, start, end)
            distance = None
            if (
                venue.location_lat is not None
                and venue.location_lng is not None
                and resource.location_lat is not None
                and resource.location_lng is not None
            ):
                distance = haversine_distance_km(
                    venue.location_lat, venue.location_lng,
                    resource.location_lat, resource.location_lng,
                )

            items.append({
                "id": str(resource.id),
                "name": resource.name,
                "description": resource.description,
                "base_price": resource.base_price,
                "currency": resource.currency,
                "rating_avg": resource.rating_avg,
                "rating_count": resource.rating_count,
                "distance_km": round(distance, 1) if distance is not None else None,
                "is_assigned": True,
                "available": available,
                "location_address": resource.location_address,
                "attributes": resource.attributes,
            })
            assigned_ids_for_type.add(resource.id)

        # 2. Radius-discovered resources of this type
        radius = addon_type.discovery_radius_km
        if (
            radius is not None
            and radius > 0
            and venue.location_lat is not None
            and venue.location_lng is not None
        ):
            all_resources_result = await session.exec(
                select(Resource).where(
                    Resource.type_id == addon_type.id,
                    Resource.status == "active",
                    Resource.location_lat.isnot(None),
                    Resource.location_lng.isnot(None),
                )
            )
            all_resources = list(all_resources_result.all())

            for resource in all_resources:
                if resource.id in assigned_ids_for_type or resource.id in assigned_addon_ids:
                    continue

                distance = haversine_distance_km(
                    venue.location_lat, venue.location_lng,
                    resource.location_lat, resource.location_lng,
                )
                if distance > radius:
                    continue

                available = await check_overlap(session, resource.id, start, end)
                items.append({
                    "id": str(resource.id),
                    "name": resource.name,
                    "description": resource.description,
                    "base_price": resource.base_price,
                    "currency": resource.currency,
                    "rating_avg": resource.rating_avg,
                    "rating_count": resource.rating_count,
                    "distance_km": round(distance, 1),
                    "is_assigned": False,
                    "available": available,
                    "location_address": resource.location_address,
                    "attributes": resource.attributes,
                })

            # Sort radius-discovered by distance
            non_assigned = [i for i in items if not i["is_assigned"]]
            assigned = [i for i in items if i["is_assigned"]]
            non_assigned.sort(key=lambda x: x["distance_km"] or 999999)
            items = assigned + non_assigned

        if items:
            result[addon_type.slug] = {
                "type_name": addon_type.name,
                "type_slug": addon_type.slug,
                "resources": items,
            }

    return result
```

- [ ] **Step 4: Run unit tests**

Run: `cd backend && python -m pytest tests/test_discovery_unit.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/domains/resources/discovery.py backend/tests/test_discovery_unit.py
git commit -m "feat(resources): add addon discovery module with Haversine distance"
```

---

### Task 6: Add Assignment CRUD & Discovery Endpoints

**Files:**
- Modify: `backend/app/domains/resources/router.py`
- Modify: `backend/app/domains/resources/service.py`

- [ ] **Step 1: Add assignment service functions**

In `backend/app/domains/resources/service.py`, add imports at top:

```python
from app.domains.resources.models import Resource, ResourceAssignment, ResourceAvailability, ResourceType
```

Add these functions at the end of the file:

```python
async def list_assignments(
    session: AsyncSession, primary_resource_id: uuid.UUID
) -> list[ResourceAssignment]:
    result = await session.exec(
        select(ResourceAssignment)
        .where(ResourceAssignment.primary_resource_id == primary_resource_id)
        .order_by(ResourceAssignment.priority)
    )
    return list(result.all())


async def create_assignment(
    session: AsyncSession,
    primary_resource_id: uuid.UUID,
    addon_resource_id: uuid.UUID,
    priority: int,
    assigned_by: uuid.UUID,
) -> ResourceAssignment:
    from fastapi import HTTPException

    if primary_resource_id == addon_resource_id:
        raise HTTPException(status_code=400, detail="Cannot assign resource to itself")

    primary = await get_resource(session, primary_resource_id)
    primary_type_result = await session.exec(
        select(ResourceType).where(ResourceType.id == primary.type_id)
    )
    primary_type = primary_type_result.first()
    if primary_type is None or primary_type.role != "primary":
        raise HTTPException(status_code=400, detail="Primary resource must have role 'primary'")

    addon = await get_resource(session, addon_resource_id)
    addon_type_result = await session.exec(
        select(ResourceType).where(ResourceType.id == addon.type_id)
    )
    addon_type = addon_type_result.first()
    if addon_type is None or addon_type.role != "addon":
        raise HTTPException(status_code=400, detail="Addon resource must have role 'addon'")

    existing = await session.exec(
        select(ResourceAssignment).where(
            ResourceAssignment.primary_resource_id == primary_resource_id,
            ResourceAssignment.addon_resource_id == addon_resource_id,
        )
    )
    if existing.first() is not None:
        raise HTTPException(status_code=409, detail="Assignment already exists")

    assignment = ResourceAssignment(
        primary_resource_id=primary_resource_id,
        addon_resource_id=addon_resource_id,
        priority=priority,
        assigned_by=assigned_by,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment


async def delete_assignment(
    session: AsyncSession, assignment_id: uuid.UUID
) -> None:
    from fastapi import HTTPException

    result = await session.exec(
        select(ResourceAssignment).where(ResourceAssignment.id == assignment_id)
    )
    assignment = result.first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await session.delete(assignment)
    await session.commit()


async def update_assignment_priority(
    session: AsyncSession, assignment_id: uuid.UUID, priority: int
) -> ResourceAssignment:
    from datetime import UTC, datetime

    from fastapi import HTTPException

    result = await session.exec(
        select(ResourceAssignment).where(ResourceAssignment.id == assignment_id)
    )
    assignment = result.first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment.priority = priority
    assignment.updated_at = datetime.now(UTC)
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment
```

- [ ] **Step 2: Add endpoints to router**

In `backend/app/domains/resources/router.py`, add imports:

```python
from datetime import datetime

from app.domains.resources.discovery import discover_addons
from app.domains.resources.schemas import (
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    HoldRequest,
    HoldResponse,
    PriceCalculateRequest,
    ReleaseRequest,
    ResourceAssignmentCreate,
    ResourceAssignmentResponse,
    ResourceAssignmentUpdate,
    ResourceCreate,
    ResourceResponse,
    ResourceTypeCreate,
    ResourceTypeResponse,
    ResourceTypeUpdate,
    ResourceUpdate,
)
from app.domains.resources.service import (
    check_availability,
    create_assignment,
    create_resource,
    create_resource_type,
    delete_assignment,
    delete_resource,
    delete_resource_type,
    get_resource,
    get_resource_type,
    get_resource_type_by_slug,
    hold_resource,
    list_assignments,
    list_resource_types,
    list_resources,
    release_resource_hold,
    update_assignment_priority,
    update_resource,
    update_resource_type,
)
```

Add endpoints to `resource_router` at end of file:

```python
# --- Addon Discovery ---

@resource_router.get("/{resource_id}/addons")
async def discover_resource_addons(
    resource_id: uuid.UUID,
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    session: AsyncSession = Depends(get_db),
):
    return await discover_addons(session, resource_id, start_date, end_date)


# --- Resource Assignments ---

@resource_router.get("/{resource_id}/assignments", response_model=list[ResourceAssignmentResponse])
async def list_resource_assignments(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("resources:*:manage")),
):
    return await list_assignments(session, resource_id)


@resource_router.post(
    "/{resource_id}/assignments",
    response_model=ResourceAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_resource_assignment(
    resource_id: uuid.UUID,
    data: ResourceAssignmentCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("resources:*:manage")),
):
    return await create_assignment(
        session, resource_id, data.addon_resource_id, data.priority, user.id
    )


@resource_router.patch(
    "/{resource_id}/assignments/{assignment_id}",
    response_model=ResourceAssignmentResponse,
)
async def update_resource_assignment(
    resource_id: uuid.UUID,
    assignment_id: uuid.UUID,
    data: ResourceAssignmentUpdate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("resources:*:manage")),
):
    return await update_assignment_priority(session, assignment_id, data.priority)


@resource_router.delete(
    "/{resource_id}/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_resource_assignment(
    resource_id: uuid.UUID,
    assignment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("resources:*:manage")),
):
    await delete_assignment(session, assignment_id)
```

Add `datetime` to the import from `Query`:

```python
from fastapi import APIRouter, Depends, Query, status
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/resources/router.py backend/app/domains/resources/service.py
git commit -m "feat(resources): add assignment CRUD and addon discovery endpoints"
```

---

### Task 7: Implement Bundled Booking Service

**Files:**
- Modify: `backend/app/domains/bookings/service.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_bundled_booking_integration.py`:

```python
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import User
from app.core.auth.password import hash_password
from app.core.tenancy.models import Tenant
from app.domains.resources.models import Resource, ResourceType
from app.main import app


@pytest.fixture
async def setup_bundled(
    db_session: AsyncSession, test_tenant: Tenant, db_engine
) -> dict:
    schema = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema}, public"))

    admin = User(
        email="bundleadmin@test.com",
        password_hash=hash_password("adminpass123"),
        full_name="Bundle Admin",
        user_type="admin",
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    venue_type = ResourceType(
        name="Venues",
        slug="venues",
        availability_model="date_range",
        pricing_model="fixed_per_day",
        role="primary",
    )
    cook_type = ResourceType(
        name="Cooks",
        slug="cooks",
        availability_model="date_range",
        pricing_model="fixed_per_day",
        role="addon",
        discovery_radius_km=50.0,
    )
    db_session.add(venue_type)
    db_session.add(cook_type)
    await db_session.commit()
    await db_session.refresh(venue_type)
    await db_session.refresh(cook_type)

    venue = Resource(
        type_id=venue_type.id,
        name="Mountain Lodge",
        base_price=5000,
        currency="INR",
        status="active",
        location_lat=30.0869,
        location_lng=78.2676,
        owner_id=admin.id,
    )
    cook = Resource(
        type_id=cook_type.id,
        name="Chef Rajesh",
        base_price=1500,
        currency="INR",
        status="active",
        location_lat=30.1,
        location_lng=78.3,
        owner_id=admin.id,
    )
    db_session.add(venue)
    db_session.add(cook)
    await db_session.commit()
    await db_session.refresh(venue)
    await db_session.refresh(cook)
    await db_session.execute(text("SET search_path TO public"))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/login",
            json={"email": "bundleadmin@test.com", "password": "adminpass123"},
            headers={"X-Tenant-ID": test_tenant.slug},
        )
        tokens = resp.json()
        headers = {
            "X-Tenant-ID": test_tenant.slug,
            "Authorization": f"Bearer {tokens['access_token']}",
        }

        yield {
            "client": client,
            "headers": headers,
            "venue": venue,
            "cook": cook,
            "tenant": test_tenant,
        }


@pytest.mark.asyncio
async def test_addon_discovery(setup_bundled):
    ctx = setup_bundled
    resp = await ctx["client"].get(
        f"/api/resources/{ctx['venue'].id}/addons",
        params={"start_date": "2026-06-01T00:00:00Z", "end_date": "2026-06-05T00:00:00Z"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "cooks" in data
    cooks = data["cooks"]["resources"]
    assert len(cooks) >= 1
    assert cooks[0]["name"] == "Chef Rajesh"


@pytest.mark.asyncio
async def test_bundled_booking_flow(setup_bundled):
    ctx = setup_bundled
    headers = ctx["headers"]
    client = ctx["client"]
    venue_id = str(ctx["venue"].id)
    cook_id = str(ctx["cook"].id)

    # Hold venue
    venue_hold = await client.post(
        f"/api/resources/{venue_id}/availability/hold",
        json={"start": "2026-06-01T00:00:00Z", "end": "2026-06-05T00:00:00Z"},
        headers=headers,
    )
    assert venue_hold.status_code == 200
    venue_token = venue_hold.json()["hold_token"]

    # Hold cook
    cook_hold = await client.post(
        f"/api/resources/{cook_id}/availability/hold",
        json={"start": "2026-06-01T00:00:00Z", "end": "2026-06-05T00:00:00Z"},
        headers=headers,
    )
    assert cook_hold.status_code == 200
    cook_token = cook_hold.json()["hold_token"]

    # Create bundled booking
    resp = await client.post(
        "/api/bookings/bundled",
        json={
            "primary": {
                "resource_id": venue_id,
                "hold_token": venue_token,
                "start_time": "2026-06-01T00:00:00Z",
                "end_time": "2026-06-05T00:00:00Z",
            },
            "addons": [
                {
                    "resource_id": cook_id,
                    "hold_token": cook_token,
                    "start_time": "2026-06-01T00:00:00Z",
                    "end_time": "2026-06-05T00:00:00Z",
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["primary"]["booking_group_id"] is not None
    assert len(data["addons"]) == 1
    assert data["addons"][0]["parent_booking_id"] == data["primary"]["id"]
    assert data["addons"][0]["booking_group_id"] == data["primary"]["booking_group_id"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_bundled_booking_integration.py -v`
Expected: FAIL — endpoint not found (404)

- [ ] **Step 3: Implement create_bundled_booking service**

In `backend/app/domains/bookings/service.py`, add at the end:

```python
async def create_bundled_booking(
    session: AsyncSession,
    primary_data: BookingCreate,
    addon_data_list: list[BookingCreate],
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> dict:
    group_id = uuid.uuid4()

    # Create primary booking
    primary_booking = await create_booking(session, primary_data, user_id, is_admin)
    primary_booking.booking_group_id = group_id
    primary_booking.parent_booking_id = None
    session.add(primary_booking)
    await session.commit()
    await session.refresh(primary_booking)

    addon_bookings = []
    for addon_data in addon_data_list:
        try:
            addon_booking = await create_booking(session, addon_data, user_id, is_admin)
            addon_booking.booking_group_id = group_id
            addon_booking.parent_booking_id = primary_booking.id
            session.add(addon_booking)
            await session.commit()
            await session.refresh(addon_booking)
            addon_bookings.append(addon_booking)
        except HTTPException:
            # If an addon booking fails, release its hold but don't fail the whole group
            if addon_data.hold_token:
                await release_hold(session, addon_data.hold_token)
            raise

    return {"primary": primary_booking, "addons": addon_bookings}
```

Add import for `BookingCreate` if not already at top (it already is via the import from schemas).

- [ ] **Step 4: Add cascade cancel logic**

In `backend/app/domains/bookings/service.py`, modify `cancel_booking` function. After `await session.refresh(booking)` and before the dispatch event call, add:

```python
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
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/domains/bookings/service.py
git commit -m "feat(bookings): add bundled booking creation and cascade cancel"
```

---

### Task 8: Add Bundled Booking & Add-Addon Endpoints

**Files:**
- Modify: `backend/app/domains/bookings/router.py`
- Modify: `backend/app/domains/bookings/schemas.py`

- [ ] **Step 1: Add bundled booking endpoint**

In `backend/app/domains/bookings/router.py`, add imports:

```python
from app.domains.bookings.schemas import (
    AddAddonRequest,
    BookingCancel,
    BookingCreate,
    BookingGroupResponse,
    BookingReject,
    BookingResponse,
    BundledBookingCreate,
)
from app.domains.bookings.service import (
    add_addon_to_booking,
    cancel_booking,
    confirm_booking,
    create_booking,
    create_bundled_booking,
    get_booking,
    list_bookings,
    mark_no_show,
    reject_booking,
)
```

Add endpoints:

```python
@router.post("/bundled", response_model=BookingGroupResponse, status_code=201)
async def create_bundled_booking_endpoint(
    data: BundledBookingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    primary_data = BookingCreate(
        resource_id=data.primary.resource_id,
        hold_token=data.primary.hold_token,
        start_time=data.primary.start_time,
        end_time=data.primary.end_time,
        notes=data.primary.notes,
        auto_confirm=data.primary.auto_confirm,
    )
    addon_data_list = [
        BookingCreate(
            resource_id=a.resource_id,
            hold_token=a.hold_token,
            start_time=a.start_time,
            end_time=a.end_time,
            notes=a.notes,
            auto_confirm=a.auto_confirm,
        )
        for a in data.addons
    ]
    result = await create_bundled_booking(
        session, primary_data, addon_data_list, user.id,
        is_admin=(user.user_type == "admin"),
    )
    return BookingGroupResponse(
        group_id=result["primary"].booking_group_id,
        primary=BookingResponse.model_validate(result["primary"]),
        addons=[BookingResponse.model_validate(a) for a in result["addons"]],
    )


@router.post("/{booking_id}/add-addon", response_model=BookingResponse, status_code=201)
async def add_addon_endpoint(
    booking_id: uuid.UUID,
    data: AddAddonRequest,
    user: User = Depends(require_permission("resources:*:assign_for_customer")),
    session: AsyncSession = Depends(get_db),
):
    return await add_addon_to_booking(
        session, booking_id, data, user.id,
        is_admin=(user.user_type == "admin"),
    )
```

- [ ] **Step 2: Implement add_addon_to_booking in service**

In `backend/app/domains/bookings/service.py`, add:

```python
async def add_addon_to_booking(
    session: AsyncSession,
    primary_booking_id: uuid.UUID,
    data,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> Booking:
    primary = await get_booking(session, primary_booking_id)
    if primary.parent_booking_id is not None:
        raise HTTPException(status_code=400, detail="Cannot add addon to an addon booking")
    if primary.status not in ("pending", "confirmed"):
        raise HTTPException(status_code=400, detail="Primary booking must be pending or confirmed")

    group_id = primary.booking_group_id or uuid.uuid4()
    if primary.booking_group_id is None:
        primary.booking_group_id = group_id
        session.add(primary)
        await session.commit()

    addon_create = BookingCreate(
        resource_id=data.resource_id,
        hold_token=data.hold_token,
        start_time=data.start_time,
        end_time=data.end_time,
        notes=data.notes,
        auto_confirm=data.auto_confirm,
    )
    addon_booking = await create_booking(session, addon_create, primary.user_id, is_admin)
    addon_booking.booking_group_id = group_id
    addon_booking.parent_booking_id = primary_booking_id
    session.add(addon_booking)
    await session.commit()
    await session.refresh(addon_booking)
    return addon_booking
```

- [ ] **Step 3: Run integration tests**

Run: `cd backend && python -m pytest tests/test_bundled_booking_integration.py -v`
Expected: ALL PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/domains/bookings/router.py backend/app/domains/bookings/service.py
git commit -m "feat(bookings): add bundled booking and add-addon endpoints"
```

---

### Task 9: Add assign_for_customer Permission

**Files:**
- Modify: `backend/app/core/auth/seed.py`

- [ ] **Step 1: Add permission to default seed**

In `backend/app/core/auth/seed.py`, add to the `DEFAULT_PERMISSIONS` list:

```python
("resources:*:assign_for_customer", "Assign addon resources to bookings on behalf of customers"),
```

Add to the `staff` role's permission set.

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/auth/seed.py
git commit -m "feat(auth): add resources:*:assign_for_customer permission"
```

---

### Task 10: Frontend — Add Addon Types

**Files:**
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Add types for addon discovery and bundled booking**

In `frontend/src/types/api.ts`, add:

```typescript
// Resource Type roles
export type ResourceTypeRole = "primary" | "addon" | "standalone" | "hidden";

// Addon Discovery
export interface AddonResource {
  id: string;
  name: string;
  description: string | null;
  base_price: number;
  currency: string;
  rating_avg: number;
  rating_count: number;
  distance_km: number | null;
  is_assigned: boolean;
  available: boolean;
  location_address: string | null;
  attributes: Record<string, unknown> | null;
}

export interface AddonTypeGroup {
  type_name: string;
  type_slug: string;
  resources: AddonResource[];
}

export type AddonDiscoveryResponse = Record<string, AddonTypeGroup>;

// Resource Assignment
export interface ResourceAssignmentResponse {
  id: string;
  primary_resource_id: string;
  addon_resource_id: string;
  priority: number;
  assigned_by: string;
  created_at: string;
  updated_at: string;
}

// Bundled Booking
export interface BookingItemCreate {
  resource_id: string;
  hold_token: string;
  start_time: string;
  end_time: string;
  notes?: string;
  auto_confirm?: boolean;
}

export interface BundledBookingCreate {
  primary: BookingItemCreate;
  addons: BookingItemCreate[];
}

export interface BookingGroupResponse {
  group_id: string;
  primary: BookingResponse;
  addons: BookingResponse[];
}

// Support Contact
export interface SupportContact {
  id: string;
  full_name: string;
  phone: string | null;
  email: string;
}
```

Also update `ResourceTypeResponse` if it exists — add role fields:

```typescript
// Add to existing ResourceTypeResponse interface:
  role: ResourceTypeRole;
  discovery_radius_km: number | null;
  display_order: number;
```

And add to `BookingResponse`:

```typescript
  parent_booking_id: string | null;
  booking_group_id: string | null;
```

And add to `ResourceResponse`:

```typescript
  support_contact_id: string | null;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/api.ts
git commit -m "feat(types): add addon discovery, assignment, and bundled booking types"
```

---

### Task 11: Frontend — Addon Discovery Hook

**Files:**
- Create: `frontend/src/hooks/use-addons.ts`

- [ ] **Step 1: Create addon hooks**

Create `frontend/src/hooks/use-addons.ts`:

```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type {
  AddonDiscoveryResponse,
  ResourceAssignmentResponse,
} from "@/types/api";

export function useAddonDiscovery(
  resourceId: string,
  startDate: string | null,
  endDate: string | null
) {
  return useQuery({
    queryKey: ["addons", resourceId, startDate, endDate],
    queryFn: async () => {
      const res = await api.get<AddonDiscoveryResponse>(
        `/resources/${resourceId}/addons`,
        { params: { start_date: startDate, end_date: endDate } }
      );
      return res.data;
    },
    enabled: !!resourceId && !!startDate && !!endDate,
  });
}

export function useResourceAssignments(resourceId: string) {
  return useQuery({
    queryKey: ["assignments", resourceId],
    queryFn: async () => {
      const res = await api.get<ResourceAssignmentResponse[]>(
        `/resources/${resourceId}/assignments`
      );
      return res.data;
    },
    enabled: !!resourceId,
  });
}

export function useCreateAssignment(resourceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { addon_resource_id: string; priority?: number }) => {
      const res = await api.post(`/resources/${resourceId}/assignments`, data);
      return res.data as ResourceAssignmentResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assignments", resourceId] }),
  });
}

export function useDeleteAssignment(resourceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (assignmentId: string) => {
      await api.delete(`/resources/${resourceId}/assignments/${assignmentId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assignments", resourceId] }),
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/hooks/use-addons.ts
git commit -m "feat(hooks): add addon discovery and assignment hooks"
```

---

### Task 12: Frontend — Addon Components

**Files:**
- Create: `frontend/src/components/public/addon-discovery-section.tsx`
- Create: `frontend/src/components/public/addon-resource-card.tsx`
- Create: `frontend/src/components/public/support-contact-card.tsx`

- [ ] **Step 1: Create addon resource card**

Create `frontend/src/components/public/addon-resource-card.tsx`:

```typescript
"use client";

import type { AddonResource } from "@/types/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface AddonResourceCardProps {
  resource: AddonResource;
  onAdd: (resource: AddonResource) => void;
  isSelected: boolean;
  onRemove: (resourceId: string) => void;
}

export function AddonResourceCard({
  resource,
  onAdd,
  isSelected,
  onRemove,
}: AddonResourceCardProps) {
  return (
    <Card className={isSelected ? "border-primary" : ""}>
      <CardContent className="flex items-center justify-between p-4">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">{resource.name}</span>
            {resource.is_assigned && (
              <Badge variant="secondary" className="text-xs">Assigned</Badge>
            )}
            {!resource.available && (
              <Badge variant="destructive" className="text-xs">Unavailable</Badge>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            {resource.distance_km !== null && (
              <span>{resource.distance_km} km away</span>
            )}
            {resource.rating_avg > 0 && (
              <span>★ {resource.rating_avg.toFixed(1)} ({resource.rating_count})</span>
            )}
          </div>
          {resource.description && (
            <p className="text-xs text-muted-foreground line-clamp-1">{resource.description}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="font-semibold">
            {resource.currency} {resource.base_price.toLocaleString()}
          </span>
          {isSelected ? (
            <Button size="sm" variant="destructive" onClick={() => onRemove(resource.id)}>
              Remove
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={() => onAdd(resource)}
              disabled={!resource.available}
            >
              Add
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Create addon discovery section**

Create `frontend/src/components/public/addon-discovery-section.tsx`:

```typescript
"use client";

import { useAddonDiscovery } from "@/hooks/use-addons";
import { AddonResourceCard } from "./addon-resource-card";
import type { AddonResource } from "@/types/api";

interface AddonDiscoverySectionProps {
  resourceId: string;
  startDate: string | null;
  endDate: string | null;
  selectedAddons: Map<string, AddonResource>;
  onAddAddon: (resource: AddonResource) => void;
  onRemoveAddon: (resourceId: string) => void;
}

export function AddonDiscoverySection({
  resourceId,
  startDate,
  endDate,
  selectedAddons,
  onAddAddon,
  onRemoveAddon,
}: AddonDiscoverySectionProps) {
  const { data, isLoading } = useAddonDiscovery(resourceId, startDate, endDate);

  if (!startDate || !endDate) {
    return (
      <p className="text-sm text-muted-foreground">
        Select dates to see available services
      </p>
    );
  }

  if (isLoading) {
    return (
      <div className="flex h-16 items-center justify-center">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!data || Object.keys(data).length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No additional services available</p>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {Object.entries(data).map(([slug, group]) => (
        <div key={slug}>
          <h4 className="mb-2 text-sm font-semibold">{group.type_name}</h4>
          <div className="flex flex-col gap-2">
            {group.resources.map((resource) => (
              <AddonResourceCard
                key={resource.id}
                resource={resource}
                isSelected={selectedAddons.has(resource.id)}
                onAdd={onAddAddon}
                onRemove={onRemoveAddon}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create support contact card**

Create `frontend/src/components/public/support-contact-card.tsx`:

```typescript
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface SupportContactCardProps {
  name: string;
  phone: string | null;
}

export function SupportContactCard({ name, phone }: SupportContactCardProps) {
  if (!phone) return null;

  const whatsappUrl = `https://wa.me/${phone.replace(/[^0-9+]/g, "")}`;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Need Help?</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <p className="text-sm">{name}</p>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" asChild>
            <a href={`tel:${phone}`}>Call</a>
          </Button>
          <Button size="sm" variant="outline" asChild>
            <a href={whatsappUrl} target="_blank" rel="noopener noreferrer">
              WhatsApp
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/public/addon-discovery-section.tsx frontend/src/components/public/addon-resource-card.tsx frontend/src/components/public/support-contact-card.tsx
git commit -m "feat(ui): add addon discovery, resource card, and support contact components"
```

---

### Task 13: Frontend — Update Public Home Page

**Files:**
- Modify: `frontend/src/app/page.tsx`

- [ ] **Step 1: Filter to primary resource types**

In `frontend/src/app/page.tsx`, where resource types are fetched and listed, add a filter so only types with `role === "primary"` or `role === "standalone"` (or no role for backwards compat) are shown. Hide `role === "addon"` and `role === "hidden"` types from the public landing page.

Find where resource types are mapped/rendered and wrap with filter:

```typescript
const visibleTypes = resourceTypes?.filter(
  (t) => !t.role || t.role === "primary" || t.role === "standalone"
);
```

Sort by `display_order`:

```typescript
const sortedTypes = visibleTypes?.sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0));
```

Use `sortedTypes` instead of `resourceTypes` in the render section.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "feat(public): filter home page to show only primary and standalone resource types"
```

---

### Task 14: Frontend — Update Resource Detail Page with Addons

**Files:**
- Modify: `frontend/src/app/(public)/resources/[id]/page.tsx`

- [ ] **Step 1: Add addon state and discovery section to resource detail**

In the resource detail page, import addon components:

```typescript
import { AddonDiscoverySection } from "@/components/public/addon-discovery-section";
import { SupportContactCard } from "@/components/public/support-contact-card";
import type { AddonResource } from "@/types/api";
```

Add state for selected addons (inside the component):

```typescript
const [selectedAddons, setSelectedAddons] = useState<Map<string, AddonResource>>(new Map());

function handleAddAddon(resource: AddonResource) {
  setSelectedAddons((prev) => new Map(prev).set(resource.id, resource));
}

function handleRemoveAddon(resourceId: string) {
  setSelectedAddons((prev) => {
    const next = new Map(prev);
    next.delete(resourceId);
    return next;
  });
}
```

Add addon discovery section after the booking card / before reviews:

```tsx
{/* Available Services */}
{resource.support_contact_id && (
  <SupportContactCard
    name="Property Manager"
    phone={null}
  />
)}

<div className="mt-6">
  <h3 className="mb-3 text-lg font-semibold">Available Services</h3>
  <AddonDiscoverySection
    resourceId={resource.id}
    startDate={bookingDates.startDate}
    endDate={bookingDates.endDate}
    selectedAddons={selectedAddons}
    onAddAddon={handleAddAddon}
    onRemoveAddon={handleRemoveAddon}
  />
</div>
```

Note: `bookingDates.startDate` and `bookingDates.endDate` should come from the booking flow state. The exact variable names depend on how `use-booking-flow.ts` exposes dates — check the hook and use the correct property names.

- [ ] **Step 2: Pass selected addons to booking flow**

When the user confirms the booking, pass selectedAddons to the bundled booking endpoint instead of the single booking endpoint. This requires modifying the checkout logic:

```typescript
// When confirming booking with addons:
if (selectedAddons.size > 0) {
  const res = await api.post("/bookings/bundled", {
    primary: {
      resource_id: resource.id,
      hold_token: holdToken,
      start_time: startDate,
      end_time: endDate,
    },
    addons: Array.from(selectedAddons.values()).map((addon) => ({
      resource_id: addon.id,
      hold_token: addonHolds.get(addon.id),
      start_time: startDate,
      end_time: endDate,
    })),
  });
} else {
  // Existing single booking flow
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/\(public\)/resources/\[id\]/page.tsx
git commit -m "feat(public): add addon discovery and bundled checkout to resource detail"
```

---

### Task 15: Frontend — Admin Resource Type Settings

**Files:**
- Modify: `frontend/src/components/resources/create-type-sheet.tsx` (or equivalent resource type edit form)

- [ ] **Step 1: Add role selector to resource type form**

In the resource type create/edit form, add fields:

```tsx
<div className="flex flex-col gap-2">
  <Label>Role</Label>
  <Select value={role} onValueChange={setRole}>
    <SelectTrigger>
      <SelectValue placeholder="Select role" />
    </SelectTrigger>
    <SelectContent>
      <SelectItem value="primary">Primary (shown on landing page)</SelectItem>
      <SelectItem value="addon">Add-on (discovered during booking)</SelectItem>
      <SelectItem value="standalone">Standalone (shown independently)</SelectItem>
      <SelectItem value="hidden">Hidden (internal only)</SelectItem>
    </SelectContent>
  </Select>
</div>

{role === "addon" && (
  <div className="flex flex-col gap-2">
    <Label>Discovery Radius (km)</Label>
    <Input
      type="number"
      value={discoveryRadius}
      onChange={(e) => setDiscoveryRadius(Number(e.target.value))}
      min={0}
      step={0.1}
    />
  </div>
)}

<div className="flex flex-col gap-2">
  <Label>Display Order</Label>
  <Input
    type="number"
    value={displayOrder}
    onChange={(e) => setDisplayOrder(Number(e.target.value))}
    min={0}
  />
</div>
```

Include these values in the form submission payload.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/resources/create-type-sheet.tsx
git commit -m "feat(admin): add role, discovery radius, and display order to resource type form"
```

---

### Task 16: Smoke Test Full Flow

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Test in browser**

Start dev servers and test:

1. **Admin:** Create venue type (role=primary), cook type (role=addon, radius=50km)
2. **Admin:** Create a venue with location, create a cook with nearby location
3. **Admin:** Optionally assign cook to venue via assignment API
4. **Public page:** Only venue type visible
5. **Resource detail:** Select dates → addon discovery section shows cook
6. **Add cook to booking → checkout shows bundled summary**
7. **Cancel venue booking → cook booking auto-cancelled**

- [ ] **Step 3: Fix any issues and commit**

```bash
git add -A
git commit -m "fix: address smoke test issues for service discovery and bundled booking"
```
