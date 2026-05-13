# Generic Resource Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the generic resource engine — admin-defined resource types with dynamic JSONB attributes, strategy-pattern availability (date_range/time_slot/hourly), strategy-pattern pricing (fixed_per_day/fixed_per_slot/per_hour/tiered), and CRUD API endpoints for resource types and individual resources.

**Architecture:** Resource types define the schema (attributes, availability model, pricing model). Resources are instances of a type with validated JSONB attributes. Availability uses a booking/hold ledger table — entries represent unavailable windows (held or booked). Strategy pattern for both availability and pricing. Pre-built templates for venues, vehicles, and cooks.

**Tech Stack:** FastAPI + SQLModel + PostgreSQL JSONB + Strategy Pattern (Protocol classes)

**Spec reference:** `docs/superpowers/specs/2026-04-28-rental-management-platform-design.md` — "Generic Resource Engine" section (lines 166-255)

---

## File Map

```
Create:
  backend/app/domains/__init__.py
  backend/app/domains/resources/__init__.py
  backend/app/domains/resources/models.py              — ResourceType, Resource, ResourceAvailability
  backend/app/domains/resources/schemas.py             — All Pydantic request/response models
  backend/app/domains/resources/attributes.py          — Dynamic attribute validation
  backend/app/domains/resources/service.py             — ResourceTypeService, ResourceService
  backend/app/domains/resources/router.py              — API endpoints for types + resources
  backend/app/domains/resources/templates.py           — Pre-built venue/vehicle/cook templates
  backend/app/domains/resources/availability/__init__.py
  backend/app/domains/resources/availability/strategy.py   — AvailabilityProvider protocol + factory
  backend/app/domains/resources/availability/date_range.py — DateRangeProvider
  backend/app/domains/resources/availability/time_slot.py  — TimeSlotProvider
  backend/app/domains/resources/availability/hourly.py     — HourlyProvider
  backend/app/domains/resources/pricing/__init__.py
  backend/app/domains/resources/pricing/strategy.py    — PricingProvider protocol + factory
  backend/app/domains/resources/pricing/providers.py   — All pricing implementations
  backend/tests/test_resource_unit.py                  — Unit tests (attributes, availability, pricing)
  backend/tests/test_resource_integration.py           — Integration tests (API flows)

Modify:
  backend/app/core/tenancy/provisioning.py             — Register resource tables
  backend/app/main.py                                  — Include resource routers
  backend/tests/conftest.py                            — Add admin user fixture
  backend/alembic/env.py                               — Import resource models
```

---

### Task 1: Domain Package + Resource Models

**Files:**
- Create: `backend/app/domains/__init__.py`
- Create: `backend/app/domains/resources/__init__.py`
- Create: `backend/app/domains/resources/models.py`
- Modify: `backend/app/core/tenancy/provisioning.py`
- Modify: `backend/alembic/env.py`
- Test: `backend/tests/test_resource_unit.py`

- [ ] **Step 1: Write failing test for model imports**

Create `backend/tests/test_resource_unit.py`:

```python
import uuid
from datetime import datetime, timezone

from app.domains.resources.models import (
    TENANT_RESOURCE_TABLES,
    Resource,
    ResourceAvailability,
    ResourceType,
)


def test_resource_type_model_fields():
    rt = ResourceType(
        name="Apartments",
        slug="apartments",
        availability_model="date_range",
        pricing_model="fixed_per_day",
    )
    assert rt.name == "Apartments"
    assert rt.slug == "apartments"
    assert rt.is_active is True
    assert isinstance(rt.id, uuid.UUID)


def test_resource_model_fields():
    r = Resource(
        type_id=uuid.uuid4(),
        name="Beach House",
        base_price=150.0,
        owner_id=uuid.uuid4(),
    )
    assert r.name == "Beach House"
    assert r.status == "draft"
    assert r.base_price == 150.0
    assert r.version == 1


def test_resource_availability_model_fields():
    ra = ResourceAvailability(
        resource_id=uuid.uuid4(),
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        status="held",
    )
    assert ra.status == "held"
    assert ra.version == 1


def test_tenant_resource_tables_registry():
    expected = {"resource_types", "resources", "resource_availability"}
    assert TENANT_RESOURCE_TABLES == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_resource_unit.py::test_resource_type_model_fields -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.domains'`

- [ ] **Step 3: Create domain package directories**

```bash
mkdir -p backend/app/domains/resources/availability
mkdir -p backend/app/domains/resources/pricing
touch backend/app/domains/__init__.py
touch backend/app/domains/resources/__init__.py
touch backend/app/domains/resources/availability/__init__.py
touch backend/app/domains/resources/pricing/__init__.py
```

- [ ] **Step 4: Implement models.py**

Create `backend/app/domains/resources/models.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TENANT_RESOURCE_TABLES: set[str] = {
    "resource_types",
    "resources",
    "resource_availability",
}


class ResourceType(SQLModel, table=True):
    __tablename__ = "resource_types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    slug: str = Field(max_length=100, index=True)
    icon: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    availability_model: str = Field(max_length=20)
    pricing_model: str = Field(max_length=20)
    attribute_schema: list | None = Field(default=None, sa_column=Column(JSONB))
    slot_config: dict | None = Field(default=None, sa_column=Column(JSONB))
    pricing_config: dict | None = Field(default=None, sa_column=Column(JSONB))
    cancellation_defaults: dict | None = Field(default=None, sa_column=Column(JSONB))
    requires_verification: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Resource(SQLModel, table=True):
    __tablename__ = "resources"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type_id: uuid.UUID = Field(foreign_key="resource_types.id", index=True)
    name: str = Field(max_length=255)
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    location_lat: float | None = Field(default=None)
    location_lng: float | None = Field(default=None)
    location_address: str | None = Field(default=None, max_length=500)
    attributes: dict | None = Field(default=None, sa_column=Column(JSONB))
    base_price: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=3)
    status: str = Field(default="draft", max_length=20)
    rating_avg: float = Field(default=0.0)
    rating_count: int = Field(default=0)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    version: int = Field(default=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ResourceAvailability(SQLModel, table=True):
    __tablename__ = "resource_availability"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resource_id: uuid.UUID = Field(foreign_key="resources.id", index=True)
    start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    end_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    status: str = Field(default="held", max_length=20)
    hold_token: str | None = Field(default=None, max_length=100, index=True)
    hold_expires: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    booking_id: uuid.UUID | None = Field(default=None)
    version: int = Field(default=1)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
```

- [ ] **Step 5: Register resource tables in provisioning.py**

In `backend/app/core/tenancy/provisioning.py`, add import and update registry:

After the existing `from app.core.auth.models import TENANT_AUTH_TABLES` line, add:

```python
from app.domains.resources.models import TENANT_RESOURCE_TABLES  # noqa: F401
```

After the existing `TENANT_TABLE_REGISTRY.update(TENANT_AUTH_TABLES)` line, add:

```python
TENANT_TABLE_REGISTRY.update(TENANT_RESOURCE_TABLES)
```

- [ ] **Step 6: Import resource models in alembic env.py**

In `backend/alembic/env.py`, add after the PlatformUser import:

```python
from app.domains.resources.models import ResourceType, Resource, ResourceAvailability  # noqa: F401
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_resource_unit.py -v`
Expected: 4 tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/domains/ backend/app/core/tenancy/provisioning.py backend/alembic/env.py backend/tests/test_resource_unit.py
git commit -m "feat(resources): add ResourceType, Resource, ResourceAvailability models"
```

---

### Task 2: Dynamic Attribute Validation

**Files:**
- Create: `backend/app/domains/resources/attributes.py`
- Test: `backend/tests/test_resource_unit.py`

Validates resource attributes dict against the resource type's attribute_schema. Schema format:
```json
[
  {"name": "bedrooms", "type": "number", "required": true, "filterable": true},
  {"name": "amenities", "type": "tags", "filterable": true},
  {"name": "property_type", "type": "enum", "options": ["house", "apartment"], "filterable": true}
]
```

Supported types: `string`, `number`, `boolean`, `enum`, `tags`.

- [ ] **Step 1: Write failing tests for attribute validation**

Append to `backend/tests/test_resource_unit.py`:

```python
from app.domains.resources.attributes import validate_attributes


def test_validate_required_attribute_present():
    schema = [{"name": "bedrooms", "type": "number", "required": True}]
    errors = validate_attributes({"bedrooms": 3}, schema)
    assert errors == []


def test_validate_required_attribute_missing():
    schema = [{"name": "bedrooms", "type": "number", "required": True}]
    errors = validate_attributes({}, schema)
    assert len(errors) == 1
    assert "bedrooms" in errors[0]


def test_validate_optional_attribute_missing():
    schema = [{"name": "notes", "type": "string", "required": False}]
    errors = validate_attributes({}, schema)
    assert errors == []


def test_validate_number_type():
    schema = [{"name": "seats", "type": "number"}]
    assert validate_attributes({"seats": 4}, schema) == []
    assert len(validate_attributes({"seats": "four"}, schema)) == 1


def test_validate_string_type():
    schema = [{"name": "color", "type": "string"}]
    assert validate_attributes({"color": "red"}, schema) == []
    assert len(validate_attributes({"color": 123}, schema)) == 1


def test_validate_boolean_type():
    schema = [{"name": "wifi", "type": "boolean"}]
    assert validate_attributes({"wifi": True}, schema) == []
    assert len(validate_attributes({"wifi": "yes"}, schema)) == 1


def test_validate_enum_type():
    schema = [{"name": "location", "type": "enum", "options": ["indoor", "outdoor"]}]
    assert validate_attributes({"location": "indoor"}, schema) == []
    assert len(validate_attributes({"location": "rooftop"}, schema)) == 1


def test_validate_tags_type():
    schema = [{"name": "amenities", "type": "tags"}]
    assert validate_attributes({"amenities": ["wifi", "pool"]}, schema) == []
    assert len(validate_attributes({"amenities": "wifi"}, schema)) == 1


def test_validate_unknown_attribute_ignored():
    schema = [{"name": "bedrooms", "type": "number"}]
    errors = validate_attributes({"bedrooms": 3, "extra_field": "val"}, schema)
    assert errors == []


def test_validate_empty_schema():
    errors = validate_attributes({"anything": "goes"}, [])
    assert errors == []


def test_validate_none_schema():
    errors = validate_attributes({"anything": "goes"}, None)
    assert errors == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_resource_unit.py::test_validate_required_attribute_present -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement attributes.py**

Create `backend/app/domains/resources/attributes.py`:

```python
def validate_attributes(
    attributes: dict | None,
    schema: list[dict] | None,
) -> list[str]:
    if not schema:
        return []
    attrs = attributes or {}
    errors: list[str] = []

    for field_def in schema:
        name = field_def["name"]
        field_type = field_def["type"]
        required = field_def.get("required", False)
        value = attrs.get(name)

        if value is None:
            if required:
                errors.append(f"Required attribute '{name}' is missing")
            continue

        type_error = _check_type(name, value, field_type, field_def)
        if type_error:
            errors.append(type_error)

    return errors


_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "tags": lambda v: isinstance(v, list) and all(isinstance(t, str) for t in v),
}


def _check_type(name: str, value, field_type: str, field_def: dict) -> str | None:
    if field_type == "enum":
        options = field_def.get("options", [])
        if value not in options:
            return f"Attribute '{name}' must be one of {options}, got '{value}'"
        return None

    checker = _TYPE_CHECKS.get(field_type)
    if checker and not checker(value):
        return f"Attribute '{name}' must be type '{field_type}', got {type(value).__name__}"
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_resource_unit.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/domains/resources/attributes.py backend/tests/test_resource_unit.py
git commit -m "feat(resources): add dynamic attribute validation against JSONB schema"
```

---

### Task 3: Availability Protocol + DateRange Provider

**Files:**
- Create: `backend/app/domains/resources/availability/strategy.py`
- Create: `backend/app/domains/resources/availability/date_range.py`
- Test: `backend/tests/test_resource_unit.py`

The availability system uses a booking/hold ledger (resource_availability table). Entries represent unavailable windows. No entry = available. Strategy pattern: each availability model validates inputs differently but all check the same overlap query.

- [ ] **Step 1: Write failing tests for availability protocol and date_range**

Append to `backend/tests/test_resource_unit.py`:

```python
from datetime import timedelta

from app.domains.resources.availability.strategy import (
    AvailabilityProvider,
    HoldResult,
    get_availability_provider,
)
from app.domains.resources.availability.date_range import DateRangeProvider


def test_get_availability_provider_date_range():
    provider = get_availability_provider("date_range")
    assert isinstance(provider, DateRangeProvider)


def test_get_availability_provider_unknown_raises():
    try:
        get_availability_provider("unknown_model")
        assert False, "Should have raised"
    except ValueError:
        pass


def test_date_range_validate_times_valid():
    provider = DateRangeProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1)
    end = now + timedelta(days=3)
    errors = provider.validate_times(start, end, slot_config=None)
    assert errors == []


def test_date_range_validate_times_end_before_start():
    provider = DateRangeProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=3)
    end = now + timedelta(days=1)
    errors = provider.validate_times(start, end, slot_config=None)
    assert len(errors) == 1


def test_date_range_validate_times_start_in_past():
    provider = DateRangeProvider()
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=1)
    errors = provider.validate_times(start, end, slot_config=None)
    assert len(errors) == 1


def test_hold_result_structure():
    result = HoldResult(hold_token="abc-123", expires=datetime.now(timezone.utc))
    assert result.hold_token == "abc-123"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_resource_unit.py::test_get_availability_provider_date_range -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement strategy.py**

Create `backend/app/domains/resources/availability/strategy.py`:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import and_, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.models import ResourceAvailability


@dataclass
class HoldResult:
    hold_token: str
    expires: datetime


class AvailabilityProvider(Protocol):
    def validate_times(
        self, start: datetime, end: datetime, slot_config: dict | None
    ) -> list[str]: ...

    async def check(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime
    ) -> bool: ...

    async def hold(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        hold_minutes: int = 10,
    ) -> HoldResult: ...


async def release_hold(session: AsyncSession, hold_token: str) -> bool:
    result = await session.exec(
        select(ResourceAvailability).where(
            ResourceAvailability.hold_token == hold_token,
            ResourceAvailability.status == "held",
        )
    )
    record = result.first()
    if record is None:
        return False
    await session.delete(record)
    await session.commit()
    return True


async def confirm_hold(session: AsyncSession, hold_token: str, booking_id: uuid.UUID) -> bool:
    result = await session.exec(
        select(ResourceAvailability).where(
            ResourceAvailability.hold_token == hold_token,
            ResourceAvailability.status == "held",
        )
    )
    record = result.first()
    if record is None:
        return False
    now = datetime.now(timezone.utc)
    if record.hold_expires and record.hold_expires < now:
        await session.delete(record)
        await session.commit()
        return False
    record.status = "booked"
    record.booking_id = booking_id
    record.hold_token = None
    record.hold_expires = None
    session.add(record)
    await session.commit()
    return True


async def check_overlap(
    session: AsyncSession,
    resource_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> bool:
    now = datetime.now(timezone.utc)
    result = await session.exec(
        select(ResourceAvailability).where(
            ResourceAvailability.resource_id == resource_id,
            ResourceAvailability.start_time < end,
            ResourceAvailability.end_time > start,
            or_(
                ResourceAvailability.status == "booked",
                and_(
                    ResourceAvailability.status == "held",
                    ResourceAvailability.hold_expires > now,
                ),
            ),
        )
    )
    return result.first() is None


async def create_hold(
    session: AsyncSession,
    resource_id: uuid.UUID,
    start: datetime,
    end: datetime,
    hold_minutes: int,
) -> HoldResult:
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(minutes=hold_minutes)
    record = ResourceAvailability(
        resource_id=resource_id,
        start_time=start,
        end_time=end,
        status="held",
        hold_token=token,
        hold_expires=expires,
    )
    session.add(record)
    await session.commit()
    return HoldResult(hold_token=token, expires=expires)


def get_availability_provider(model: str) -> AvailabilityProvider:
    from app.domains.resources.availability.date_range import DateRangeProvider
    from app.domains.resources.availability.hourly import HourlyProvider
    from app.domains.resources.availability.time_slot import TimeSlotProvider

    providers: dict[str, AvailabilityProvider] = {
        "date_range": DateRangeProvider(),
        "time_slot": TimeSlotProvider(),
        "hourly": HourlyProvider(),
    }
    if model not in providers:
        raise ValueError(f"Unknown availability model: {model}")
    return providers[model]
```

- [ ] **Step 4: Implement date_range.py**

Create `backend/app/domains/resources/availability/date_range.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.availability.strategy import (
    HoldResult,
    check_overlap,
    create_hold,
)


class DateRangeProvider:
    def validate_times(
        self, start: datetime, end: datetime, slot_config: dict | None
    ) -> list[str]:
        errors: list[str] = []
        now = datetime.now(timezone.utc)
        if start < now:
            errors.append("Start time cannot be in the past")
        if end <= start:
            errors.append("End time must be after start time")
        return errors

    async def check(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime
    ) -> bool:
        return await check_overlap(session, resource_id, start, end)

    async def hold(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        hold_minutes: int = 10,
    ) -> HoldResult:
        available = await self.check(session, resource_id, start, end)
        if not available:
            raise ValueError("Resource not available for requested dates")
        return await create_hold(session, resource_id, start, end, hold_minutes)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_resource_unit.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/domains/resources/availability/ backend/tests/test_resource_unit.py
git commit -m "feat(resources): add availability protocol and date_range provider"
```

---

### Task 4: TimeSlot + Hourly Availability Providers

**Files:**
- Create: `backend/app/domains/resources/availability/time_slot.py`
- Create: `backend/app/domains/resources/availability/hourly.py`
- Test: `backend/tests/test_resource_unit.py`

- [ ] **Step 1: Write failing tests for time_slot and hourly**

Append to `backend/tests/test_resource_unit.py`:

```python
from app.domains.resources.availability.time_slot import TimeSlotProvider
from app.domains.resources.availability.hourly import HourlyProvider


def test_time_slot_validate_times_valid():
    provider = TimeSlotProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=1, minutes=30)
    slot_config = {"duration_options": ["1h", "1.5h", "2h"], "buffer_between": "30min"}
    errors = provider.validate_times(start, end, slot_config)
    assert errors == []


def test_time_slot_validate_times_invalid_duration():
    provider = TimeSlotProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=3)
    slot_config = {"duration_options": ["1h", "1.5h", "2h"], "buffer_between": "30min"}
    errors = provider.validate_times(start, end, slot_config)
    assert len(errors) == 1


def test_time_slot_validate_no_config():
    provider = TimeSlotProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=1)
    errors = provider.validate_times(start, end, slot_config=None)
    assert errors == []


def test_hourly_validate_times_valid():
    provider = HourlyProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(hours=4)
    errors = provider.validate_times(start, end, slot_config=None)
    assert errors == []


def test_hourly_validate_times_end_before_start():
    provider = HourlyProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=5)
    end = now + timedelta(hours=1)
    errors = provider.validate_times(start, end, slot_config=None)
    assert len(errors) == 1


def test_hourly_validate_times_minimum_duration():
    provider = HourlyProvider()
    now = datetime.now(timezone.utc)
    start = now + timedelta(hours=1)
    end = start + timedelta(minutes=15)
    errors = provider.validate_times(start, end, slot_config=None)
    assert len(errors) == 1


def test_get_provider_time_slot():
    provider = get_availability_provider("time_slot")
    assert isinstance(provider, TimeSlotProvider)


def test_get_provider_hourly():
    provider = get_availability_provider("hourly")
    assert isinstance(provider, HourlyProvider)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_resource_unit.py::test_time_slot_validate_times_valid -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement time_slot.py**

Create `backend/app/domains/resources/availability/time_slot.py`:

```python
import re
import uuid
from datetime import datetime, timezone

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.availability.strategy import (
    HoldResult,
    check_overlap,
    create_hold,
)


def _parse_duration(s: str) -> float:
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(h|min)$", s)
    if not match:
        return 0
    val, unit = float(match.group(1)), match.group(2)
    return val * 60 if unit == "h" else val


class TimeSlotProvider:
    def validate_times(
        self, start: datetime, end: datetime, slot_config: dict | None
    ) -> list[str]:
        errors: list[str] = []
        now = datetime.now(timezone.utc)
        if start < now:
            errors.append("Start time cannot be in the past")
        if end <= start:
            errors.append("End time must be after start time")
            return errors

        if slot_config:
            duration_minutes = (end - start).total_seconds() / 60
            allowed = [_parse_duration(d) for d in slot_config.get("duration_options", [])]
            if allowed and not any(abs(duration_minutes - a) < 1 for a in allowed):
                errors.append(
                    f"Slot duration {duration_minutes:.0f}min not in allowed: "
                    f"{slot_config.get('duration_options')}"
                )
        return errors

    async def check(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime
    ) -> bool:
        return await check_overlap(session, resource_id, start, end)

    async def hold(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        hold_minutes: int = 10,
    ) -> HoldResult:
        available = await self.check(session, resource_id, start, end)
        if not available:
            raise ValueError("Time slot not available")
        return await create_hold(session, resource_id, start, end, hold_minutes)
```

- [ ] **Step 4: Implement hourly.py**

Create `backend/app/domains/resources/availability/hourly.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.availability.strategy import (
    HoldResult,
    check_overlap,
    create_hold,
)

MINIMUM_HOURS = 0.5


class HourlyProvider:
    def validate_times(
        self, start: datetime, end: datetime, slot_config: dict | None
    ) -> list[str]:
        errors: list[str] = []
        now = datetime.now(timezone.utc)
        if start < now:
            errors.append("Start time cannot be in the past")
        if end <= start:
            errors.append("End time must be after start time")
            return errors

        hours = (end - start).total_seconds() / 3600
        if hours < MINIMUM_HOURS:
            errors.append(f"Minimum booking duration is {MINIMUM_HOURS} hours")
        return errors

    async def check(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime
    ) -> bool:
        return await check_overlap(session, resource_id, start, end)

    async def hold(
        self, session: AsyncSession, resource_id: uuid.UUID, start: datetime, end: datetime,
        hold_minutes: int = 10,
    ) -> HoldResult:
        available = await self.check(session, resource_id, start, end)
        if not available:
            raise ValueError("Resource not available for requested hours")
        return await create_hold(session, resource_id, start, end, hold_minutes)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_resource_unit.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/domains/resources/availability/time_slot.py backend/app/domains/resources/availability/hourly.py backend/tests/test_resource_unit.py
git commit -m "feat(resources): add time_slot and hourly availability providers"
```

---

### Task 5: Pricing Protocol + All Providers

**Files:**
- Create: `backend/app/domains/resources/pricing/strategy.py`
- Create: `backend/app/domains/resources/pricing/providers.py`
- Test: `backend/tests/test_resource_unit.py`

Pricing models: fixed_per_day, fixed_per_slot, per_hour, tiered. Each takes start/end times + base_price + optional config and returns total price.

- [ ] **Step 1: Write failing tests for pricing**

Append to `backend/tests/test_resource_unit.py`:

```python
from app.domains.resources.pricing.strategy import get_pricing_provider
from app.domains.resources.pricing.providers import (
    FixedPerDayProvider,
    FixedPerSlotProvider,
    HourlyPricingProvider,
    TieredProvider,
)


def test_fixed_per_day_pricing():
    provider = FixedPerDayProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=3)
    price = provider.calculate(base_price=100.0, start=start, end=end, config=None)
    assert price == 300.0


def test_fixed_per_day_partial_day_rounds_up():
    provider = FixedPerDayProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=2, hours=6)
    price = provider.calculate(base_price=100.0, start=start, end=end, config=None)
    assert price == 300.0


def test_fixed_per_slot_pricing():
    provider = FixedPerSlotProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(hours=1, minutes=30)
    price = provider.calculate(base_price=50.0, start=start, end=end, config=None)
    assert price == 50.0


def test_hourly_pricing():
    provider = HourlyPricingProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(hours=4)
    price = provider.calculate(base_price=25.0, start=start, end=end, config=None)
    assert price == 100.0


def test_hourly_pricing_partial_hour():
    provider = HourlyPricingProvider()
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(hours=2, minutes=30)
    price = provider.calculate(base_price=20.0, start=start, end=end, config=None)
    assert price == 60.0


def test_tiered_pricing():
    provider = TieredProvider()
    config = {
        "tiers": [
            {"min_days": 1, "max_days": 3, "rate_multiplier": 1.0},
            {"min_days": 4, "max_days": 7, "rate_multiplier": 0.85},
            {"min_days": 8, "max_days": None, "rate_multiplier": 0.70},
        ]
    }
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=10)
    price = provider.calculate(base_price=100.0, start=start, end=end, config=config)
    # Days 1-3: 3 * 100 * 1.0 = 300
    # Days 4-7: 4 * 100 * 0.85 = 340
    # Days 8-10: 3 * 100 * 0.70 = 210
    assert price == 850.0


def test_tiered_pricing_short_stay():
    provider = TieredProvider()
    config = {
        "tiers": [
            {"min_days": 1, "max_days": 3, "rate_multiplier": 1.0},
            {"min_days": 4, "max_days": 7, "rate_multiplier": 0.85},
        ]
    }
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(days=2)
    price = provider.calculate(base_price=100.0, start=start, end=end, config=config)
    assert price == 200.0


def test_get_pricing_provider_all_models():
    assert isinstance(get_pricing_provider("fixed_per_day"), FixedPerDayProvider)
    assert isinstance(get_pricing_provider("fixed_per_slot"), FixedPerSlotProvider)
    assert isinstance(get_pricing_provider("per_hour"), HourlyPricingProvider)
    assert isinstance(get_pricing_provider("tiered"), TieredProvider)


def test_get_pricing_provider_unknown_raises():
    try:
        get_pricing_provider("unknown")
        assert False, "Should have raised"
    except ValueError:
        pass
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_resource_unit.py::test_fixed_per_day_pricing -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement pricing strategy.py**

Create `backend/app/domains/resources/pricing/strategy.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Protocol


class PricingProvider(Protocol):
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float: ...


def get_pricing_provider(model: str) -> PricingProvider:
    from app.domains.resources.pricing.providers import (
        FixedPerDayProvider,
        FixedPerSlotProvider,
        HourlyPricingProvider,
        TieredProvider,
    )

    providers: dict[str, PricingProvider] = {
        "fixed_per_day": FixedPerDayProvider(),
        "fixed_per_slot": FixedPerSlotProvider(),
        "per_hour": HourlyPricingProvider(),
        "tiered": TieredProvider(),
    }
    if model not in providers:
        raise ValueError(f"Unknown pricing model: {model}")
    return providers[model]
```

- [ ] **Step 4: Implement providers.py**

Create `backend/app/domains/resources/pricing/providers.py`:

```python
import math
from datetime import datetime


class FixedPerDayProvider:
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float:
        days = math.ceil((end - start).total_seconds() / 86400)
        return base_price * max(days, 1)


class FixedPerSlotProvider:
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float:
        return base_price


class HourlyPricingProvider:
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float:
        hours = math.ceil((end - start).total_seconds() / 3600)
        return base_price * max(hours, 1)


class TieredProvider:
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float:
        total_days = math.ceil((end - start).total_seconds() / 86400)
        total_days = max(total_days, 1)
        if not config or "tiers" not in config:
            return base_price * total_days

        tiers = sorted(config["tiers"], key=lambda t: t["min_days"])
        total = 0.0
        remaining = total_days

        for tier in tiers:
            min_d = tier["min_days"]
            max_d = tier.get("max_days")
            multiplier = tier.get("rate_multiplier", 1.0)

            if remaining <= 0:
                break

            if max_d is None:
                days_in_tier = remaining
            else:
                tier_span = max_d - min_d + 1
                days_in_tier = min(remaining, tier_span)

            total += days_in_tier * base_price * multiplier
            remaining -= days_in_tier

        if remaining > 0:
            total += remaining * base_price

        return round(total, 2)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_resource_unit.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/domains/resources/pricing/ backend/tests/test_resource_unit.py
git commit -m "feat(resources): add pricing strategy with fixed, hourly, and tiered providers"
```

---

### Task 6: Resource Type Schemas + Service

**Files:**
- Create: `backend/app/domains/resources/schemas.py`
- Create: `backend/app/domains/resources/service.py`
- Test: `backend/tests/test_resource_unit.py`

- [ ] **Step 1: Write failing tests for schemas and service imports**

Append to `backend/tests/test_resource_unit.py`:

```python
from pydantic import ValidationError

from app.domains.resources.schemas import (
    ResourceTypeCreate,
    ResourceTypeResponse,
    ResourceTypeUpdate,
)


def test_resource_type_create_valid():
    data = ResourceTypeCreate(
        name="Apartments",
        slug="apartments",
        availability_model="date_range",
        pricing_model="fixed_per_day",
    )
    assert data.name == "Apartments"


def test_resource_type_create_invalid_availability_model():
    try:
        ResourceTypeCreate(
            name="Test",
            slug="test",
            availability_model="invalid_model",
            pricing_model="fixed_per_day",
        )
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_resource_type_create_invalid_pricing_model():
    try:
        ResourceTypeCreate(
            name="Test",
            slug="test",
            availability_model="date_range",
            pricing_model="invalid_model",
        )
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_resource_type_update_partial():
    data = ResourceTypeUpdate(name="Updated Name")
    assert data.name == "Updated Name"
    assert data.slug is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_resource_unit.py::test_resource_type_create_valid -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement schemas.py**

Create `backend/app/domains/resources/schemas.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator

VALID_AVAILABILITY_MODELS = {"date_range", "time_slot", "hourly"}
VALID_PRICING_MODELS = {"fixed_per_day", "fixed_per_slot", "per_hour", "tiered"}
VALID_RESOURCE_STATUSES = {"draft", "active", "inactive", "archived"}


class ResourceTypeCreate(BaseModel):
    name: str
    slug: str
    icon: str | None = None
    description: str | None = None
    availability_model: str
    pricing_model: str
    attribute_schema: list[dict] | None = None
    slot_config: dict | None = None
    pricing_config: dict | None = None
    cancellation_defaults: dict | None = None
    requires_verification: bool = False

    @field_validator("availability_model")
    @classmethod
    def check_availability_model(cls, v: str) -> str:
        if v not in VALID_AVAILABILITY_MODELS:
            raise ValueError(f"Must be one of {VALID_AVAILABILITY_MODELS}")
        return v

    @field_validator("pricing_model")
    @classmethod
    def check_pricing_model(cls, v: str) -> str:
        if v not in VALID_PRICING_MODELS:
            raise ValueError(f"Must be one of {VALID_PRICING_MODELS}")
        return v


class ResourceTypeUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    icon: str | None = None
    description: str | None = None
    attribute_schema: list[dict] | None = None
    slot_config: dict | None = None
    pricing_config: dict | None = None
    cancellation_defaults: dict | None = None
    requires_verification: bool | None = None
    is_active: bool | None = None


class ResourceTypeResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    icon: str | None
    description: str | None
    availability_model: str
    pricing_model: str
    attribute_schema: list[dict] | None
    slot_config: dict | None
    pricing_config: dict | None
    cancellation_defaults: dict | None
    requires_verification: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResourceCreate(BaseModel):
    type_id: uuid.UUID
    name: str
    description: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    location_address: str | None = None
    attributes: dict | None = None
    base_price: float
    currency: str = "USD"

    @field_validator("base_price")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v


class ResourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location_lat: float | None = None
    location_lng: float | None = None
    location_address: str | None = None
    attributes: dict | None = None
    base_price: float | None = None
    currency: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def check_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_RESOURCE_STATUSES:
            raise ValueError(f"Must be one of {VALID_RESOURCE_STATUSES}")
        return v

    @field_validator("base_price")
    @classmethod
    def price_positive(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("Price must be non-negative")
        return v


class ResourceResponse(BaseModel):
    id: uuid.UUID
    type_id: uuid.UUID
    name: str
    description: str | None
    location_lat: float | None
    location_lng: float | None
    location_address: str | None
    attributes: dict | None
    base_price: float
    currency: str
    status: str
    rating_avg: float
    rating_count: int
    owner_id: uuid.UUID
    version: int
    created_at: datetime
    updated_at: datetime


class AvailabilityCheckRequest(BaseModel):
    start: datetime
    end: datetime


class AvailabilityCheckResponse(BaseModel):
    available: bool
    price: float | None = None


class HoldRequest(BaseModel):
    start: datetime
    end: datetime
    hold_minutes: int = 10


class HoldResponse(BaseModel):
    hold_token: str
    expires: datetime
    price: float


class ReleaseRequest(BaseModel):
    hold_token: str


class PriceCalculateRequest(BaseModel):
    start: datetime
    end: datetime
```

- [ ] **Step 4: Implement service.py**

Create `backend/app/domains/resources/service.py`:

```python
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domains.resources.attributes import validate_attributes
from app.domains.resources.availability.strategy import (
    get_availability_provider,
    release_hold,
)
from app.domains.resources.models import Resource, ResourceType
from app.domains.resources.pricing.strategy import get_pricing_provider
from app.domains.resources.schemas import (
    ResourceCreate,
    ResourceTypeCreate,
    ResourceTypeUpdate,
    ResourceUpdate,
)


async def create_resource_type(
    session: AsyncSession, data: ResourceTypeCreate
) -> ResourceType:
    result = await session.exec(
        select(ResourceType).where(ResourceType.slug == data.slug)
    )
    if result.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Resource type with slug '{data.slug}' already exists",
        )

    rt = ResourceType(
        name=data.name,
        slug=data.slug,
        icon=data.icon,
        description=data.description,
        availability_model=data.availability_model,
        pricing_model=data.pricing_model,
        attribute_schema=data.attribute_schema,
        slot_config=data.slot_config,
        pricing_config=data.pricing_config,
        cancellation_defaults=data.cancellation_defaults,
        requires_verification=data.requires_verification,
    )
    session.add(rt)
    await session.commit()
    await session.refresh(rt)
    return rt


async def list_resource_types(
    session: AsyncSession, active_only: bool = True
) -> list[ResourceType]:
    stmt = select(ResourceType)
    if active_only:
        stmt = stmt.where(ResourceType.is_active == True)
    result = await session.exec(stmt.order_by(ResourceType.name))
    return list(result.all())


async def get_resource_type(
    session: AsyncSession, resource_type_id: uuid.UUID
) -> ResourceType:
    result = await session.exec(
        select(ResourceType).where(ResourceType.id == resource_type_id)
    )
    rt = result.first()
    if rt is None:
        raise HTTPException(status_code=404, detail="Resource type not found")
    return rt


async def get_resource_type_by_slug(
    session: AsyncSession, slug: str
) -> ResourceType:
    result = await session.exec(
        select(ResourceType).where(ResourceType.slug == slug)
    )
    rt = result.first()
    if rt is None:
        raise HTTPException(status_code=404, detail="Resource type not found")
    return rt


async def update_resource_type(
    session: AsyncSession, resource_type_id: uuid.UUID, data: ResourceTypeUpdate
) -> ResourceType:
    rt = await get_resource_type(session, resource_type_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rt, key, value)
    rt.updated_at = datetime.now(timezone.utc)
    session.add(rt)
    await session.commit()
    await session.refresh(rt)
    return rt


async def delete_resource_type(
    session: AsyncSession, resource_type_id: uuid.UUID
) -> None:
    rt = await get_resource_type(session, resource_type_id)
    rt.is_active = False
    rt.updated_at = datetime.now(timezone.utc)
    session.add(rt)
    await session.commit()


async def create_resource(
    session: AsyncSession, data: ResourceCreate, owner_id: uuid.UUID
) -> Resource:
    rt = await get_resource_type(session, data.type_id)
    if not rt.is_active:
        raise HTTPException(
            status_code=400, detail="Cannot create resource for inactive type"
        )

    if data.attributes and rt.attribute_schema:
        errors = validate_attributes(data.attributes, rt.attribute_schema)
        if errors:
            raise HTTPException(status_code=422, detail={"attribute_errors": errors})

    resource = Resource(
        type_id=data.type_id,
        name=data.name,
        description=data.description,
        location_lat=data.location_lat,
        location_lng=data.location_lng,
        location_address=data.location_address,
        attributes=data.attributes,
        base_price=data.base_price,
        currency=data.currency,
        owner_id=owner_id,
    )
    session.add(resource)
    await session.commit()
    await session.refresh(resource)
    return resource


async def list_resources(
    session: AsyncSession,
    type_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    owner_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Resource]:
    stmt = select(Resource)
    if type_id:
        stmt = stmt.where(Resource.type_id == type_id)
    if status_filter:
        stmt = stmt.where(Resource.status == status_filter)
    if owner_id:
        stmt = stmt.where(Resource.owner_id == owner_id)
    stmt = stmt.offset(offset).limit(limit).order_by(Resource.created_at.desc())
    result = await session.exec(stmt)
    return list(result.all())


async def get_resource(session: AsyncSession, resource_id: uuid.UUID) -> Resource:
    result = await session.exec(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource


async def update_resource(
    session: AsyncSession,
    resource_id: uuid.UUID,
    data: ResourceUpdate,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> Resource:
    resource = await get_resource(session, resource_id)
    if not is_admin and resource.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not the resource owner")

    if data.attributes is not None:
        rt = await get_resource_type(session, resource.type_id)
        if rt.attribute_schema:
            errors = validate_attributes(data.attributes, rt.attribute_schema)
            if errors:
                raise HTTPException(
                    status_code=422, detail={"attribute_errors": errors}
                )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(resource, key, value)
    resource.updated_at = datetime.now(timezone.utc)
    resource.version += 1
    session.add(resource)
    await session.commit()
    await session.refresh(resource)
    return resource


async def delete_resource(
    session: AsyncSession,
    resource_id: uuid.UUID,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> None:
    resource = await get_resource(session, resource_id)
    if not is_admin and resource.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Not the resource owner")
    resource.status = "archived"
    resource.updated_at = datetime.now(timezone.utc)
    session.add(resource)
    await session.commit()


async def check_availability(
    session: AsyncSession,
    resource_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> tuple[bool, float | None]:
    resource = await get_resource(session, resource_id)
    rt = await get_resource_type(session, resource.type_id)

    provider = get_availability_provider(rt.availability_model)
    errors = provider.validate_times(start, end, rt.slot_config)
    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    available = await provider.check(session, resource.id, start, end)
    price = None
    if available:
        pricing = get_pricing_provider(rt.pricing_model)
        price = pricing.calculate(resource.base_price, start, end, rt.pricing_config)

    return available, price


async def hold_resource(
    session: AsyncSession,
    resource_id: uuid.UUID,
    start: datetime,
    end: datetime,
    hold_minutes: int = 10,
) -> tuple[str, datetime, float]:
    resource = await get_resource(session, resource_id)
    if resource.status != "active":
        raise HTTPException(status_code=400, detail="Resource is not active")

    rt = await get_resource_type(session, resource.type_id)
    provider = get_availability_provider(rt.availability_model)

    errors = provider.validate_times(start, end, rt.slot_config)
    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    try:
        result = await provider.hold(
            session, resource.id, start, end, hold_minutes=hold_minutes
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    pricing = get_pricing_provider(rt.pricing_model)
    price = pricing.calculate(resource.base_price, start, end, rt.pricing_config)
    return result.hold_token, result.expires, price


async def release_resource_hold(session: AsyncSession, hold_token: str) -> bool:
    released = await release_hold(session, hold_token)
    if not released:
        raise HTTPException(status_code=404, detail="Hold not found")
    return True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_resource_unit.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/domains/resources/schemas.py backend/app/domains/resources/service.py backend/tests/test_resource_unit.py
git commit -m "feat(resources): add resource type/resource schemas and service layer"
```

---

### Task 7: Pre-built Resource Type Templates

**Files:**
- Create: `backend/app/domains/resources/templates.py`
- Test: `backend/tests/test_resource_unit.py`

Venues, vehicles, and cooks — pre-built configurations that admins can use as-is or customize.

- [ ] **Step 1: Write failing tests for templates**

Append to `backend/tests/test_resource_unit.py`:

```python
from app.domains.resources.templates import RESOURCE_TYPE_TEMPLATES


def test_templates_have_required_keys():
    required = {"name", "slug", "availability_model", "pricing_model", "attribute_schema"}
    for slug, tmpl in RESOURCE_TYPE_TEMPLATES.items():
        assert required.issubset(tmpl.keys()), f"Template '{slug}' missing keys"


def test_venues_template():
    tmpl = RESOURCE_TYPE_TEMPLATES["venues"]
    assert tmpl["availability_model"] == "date_range"
    assert tmpl["pricing_model"] == "fixed_per_day"
    attr_names = {a["name"] for a in tmpl["attribute_schema"]}
    assert "bedrooms" in attr_names
    assert "property_type" in attr_names


def test_vehicles_template():
    tmpl = RESOURCE_TYPE_TEMPLATES["vehicles"]
    assert tmpl["availability_model"] == "hourly"
    assert tmpl["pricing_model"] == "per_hour"
    attr_names = {a["name"] for a in tmpl["attribute_schema"]}
    assert "vehicle_type" in attr_names
    assert "seats" in attr_names


def test_cooks_template():
    tmpl = RESOURCE_TYPE_TEMPLATES["cooks"]
    assert tmpl["availability_model"] == "time_slot"
    assert tmpl["pricing_model"] == "fixed_per_slot"
    attr_names = {a["name"] for a in tmpl["attribute_schema"]}
    assert "cuisine_type" in attr_names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_resource_unit.py::test_templates_have_required_keys -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement templates.py**

Create `backend/app/domains/resources/templates.py`:

```python
RESOURCE_TYPE_TEMPLATES: dict[str, dict] = {
    "venues": {
        "name": "Venues",
        "slug": "venues",
        "icon": "building",
        "description": "Apartments, houses, event spaces, and other rentable venues",
        "availability_model": "date_range",
        "pricing_model": "fixed_per_day",
        "attribute_schema": [
            {"name": "property_type", "type": "enum", "options": ["apartment", "house", "villa", "studio", "event_space"], "required": True, "filterable": True},
            {"name": "bedrooms", "type": "number", "required": True, "filterable": True},
            {"name": "bathrooms", "type": "number", "required": True, "filterable": True},
            {"name": "max_guests", "type": "number", "required": True, "filterable": True},
            {"name": "amenities", "type": "tags", "required": False, "filterable": True},
            {"name": "pet_friendly", "type": "boolean", "required": False, "filterable": True},
        ],
        "cancellation_defaults": {
            "free_cancel_hours": 48,
            "partial_cancel_hours": 24,
            "partial_refund_percent": 50,
            "no_refund_after": True,
        },
    },
    "vehicles": {
        "name": "Vehicles",
        "slug": "vehicles",
        "icon": "car",
        "description": "Cars, bikes, scooters, vans, and other vehicles for rent",
        "availability_model": "hourly",
        "pricing_model": "per_hour",
        "attribute_schema": [
            {"name": "vehicle_type", "type": "enum", "options": ["car", "bike", "scooter", "van", "truck", "electric_bike"], "required": True, "filterable": True},
            {"name": "seats", "type": "number", "required": True, "filterable": True},
            {"name": "fuel_type", "type": "enum", "options": ["petrol", "diesel", "electric", "hybrid", "none"], "required": True, "filterable": True},
            {"name": "transmission", "type": "enum", "options": ["manual", "automatic"], "required": False, "filterable": True},
            {"name": "features", "type": "tags", "required": False, "filterable": True},
        ],
        "cancellation_defaults": {
            "free_cancel_hours": 4,
            "no_refund_after": True,
        },
    },
    "cooks": {
        "name": "Cooks",
        "slug": "cooks",
        "icon": "chef-hat",
        "description": "Private cooks and chefs available for hire by time slot",
        "availability_model": "time_slot",
        "pricing_model": "fixed_per_slot",
        "slot_config": {
            "duration_options": ["1h", "1.5h", "2h", "3h"],
            "buffer_between": "30min",
        },
        "attribute_schema": [
            {"name": "cuisine_type", "type": "tags", "required": True, "filterable": True},
            {"name": "experience_years", "type": "number", "required": True, "filterable": True},
            {"name": "specialties", "type": "tags", "required": False, "filterable": True},
            {"name": "max_guests_served", "type": "number", "required": True, "filterable": True},
            {"name": "brings_own_ingredients", "type": "boolean", "required": False, "filterable": True},
        ],
        "cancellation_defaults": {
            "free_cancel_hours": 24,
            "partial_cancel_hours": 12,
            "partial_refund_percent": 50,
            "no_refund_after": True,
        },
    },
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_resource_unit.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/domains/resources/templates.py backend/tests/test_resource_unit.py
git commit -m "feat(resources): add pre-built templates for venues, vehicles, and cooks"
```

---

### Task 8: Resource Type Router

**Files:**
- Create: `backend/app/domains/resources/router.py`
- Modify: `backend/app/main.py`

Admin endpoints for managing resource types. Includes a `/from-template/{template_slug}` endpoint to create a type from a pre-built template.

- [ ] **Step 1: Implement router.py**

Create `backend/app/domains/resources/router.py`:

```python
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user, require_permission
from app.core.auth.models import User
from app.database import get_db
from app.domains.resources.models import ResourceType
from app.domains.resources.schemas import (
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    HoldRequest,
    HoldResponse,
    PriceCalculateRequest,
    ReleaseRequest,
    ResourceCreate,
    ResourceResponse,
    ResourceTypeCreate,
    ResourceTypeResponse,
    ResourceTypeUpdate,
    ResourceUpdate,
)
from app.domains.resources.service import (
    check_availability,
    create_resource,
    create_resource_type,
    delete_resource,
    delete_resource_type,
    get_resource,
    get_resource_type,
    get_resource_type_by_slug,
    hold_resource,
    list_resource_types,
    list_resources,
    release_resource_hold,
    update_resource,
    update_resource_type,
)
from app.domains.resources.templates import RESOURCE_TYPE_TEMPLATES

resource_type_router = APIRouter(prefix="/api/resource-types", tags=["resource-types"])
resource_router = APIRouter(prefix="/api/resources", tags=["resources"])


@resource_type_router.get("/", response_model=list[ResourceTypeResponse])
async def list_types(
    active_only: bool = Query(True),
    session: AsyncSession = Depends(get_db),
):
    return await list_resource_types(session, active_only=active_only)


@resource_type_router.get("/templates")
async def list_templates():
    return {
        slug: {"slug": slug, "name": t["name"], "description": t.get("description")}
        for slug, t in RESOURCE_TYPE_TEMPLATES.items()
    }


@resource_type_router.get("/{slug}", response_model=ResourceTypeResponse)
async def get_type_by_slug(
    slug: str,
    session: AsyncSession = Depends(get_db),
):
    return await get_resource_type_by_slug(session, slug)


@resource_type_router.post(
    "/",
    response_model=ResourceTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_type(
    data: ResourceTypeCreate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("resources:*:manage")),
):
    return await create_resource_type(session, data)


@resource_type_router.post(
    "/from-template/{template_slug}",
    response_model=ResourceTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_type_from_template(
    template_slug: str,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("resources:*:manage")),
):
    tmpl = RESOURCE_TYPE_TEMPLATES.get(template_slug)
    if tmpl is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Template '{template_slug}' not found")
    data = ResourceTypeCreate(**tmpl)
    return await create_resource_type(session, data)


@resource_type_router.put("/{resource_type_id}", response_model=ResourceTypeResponse)
async def update_type(
    resource_type_id: uuid.UUID,
    data: ResourceTypeUpdate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("resources:*:manage")),
):
    return await update_resource_type(session, resource_type_id, data)


@resource_type_router.delete("/{resource_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_type(
    resource_type_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("resources:*:manage")),
):
    await delete_resource_type(session, resource_type_id)


# --- Resource endpoints ---

@resource_router.get("/", response_model=list[ResourceResponse])
async def list_all_resources(
    type_id: uuid.UUID | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    return await list_resources(
        session, type_id=type_id, status_filter=status_filter, offset=offset, limit=limit
    )


@resource_router.get("/{resource_id}", response_model=ResourceResponse)
async def get_one_resource(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    return await get_resource(session, resource_id)


@resource_router.post(
    "/",
    response_model=ResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_one_resource(
    data: ResourceCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("resources:*:create")),
):
    return await create_resource(session, data, owner_id=user.id)


@resource_router.put("/{resource_id}", response_model=ResourceResponse)
async def update_one_resource(
    resource_id: uuid.UUID,
    data: ResourceUpdate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    is_admin = user.user_type == "admin"
    return await update_resource(session, resource_id, data, user.id, is_admin=is_admin)


@resource_router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_one_resource(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    is_admin = user.user_type == "admin"
    await delete_resource(session, resource_id, user.id, is_admin=is_admin)


@resource_router.post("/{resource_id}/availability/check", response_model=AvailabilityCheckResponse)
async def check_resource_availability(
    resource_id: uuid.UUID,
    data: AvailabilityCheckRequest,
    session: AsyncSession = Depends(get_db),
):
    available, price = await check_availability(session, resource_id, data.start, data.end)
    return AvailabilityCheckResponse(available=available, price=price)


@resource_router.post("/{resource_id}/availability/hold", response_model=HoldResponse)
async def hold_resource_availability(
    resource_id: uuid.UUID,
    data: HoldRequest,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    token, expires, price = await hold_resource(
        session, resource_id, data.start, data.end, data.hold_minutes
    )
    return HoldResponse(hold_token=token, expires=expires, price=price)


@resource_router.post("/{resource_id}/availability/release")
async def release_resource_availability(
    resource_id: uuid.UUID,
    data: ReleaseRequest,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    await release_resource_hold(session, data.hold_token)
    return {"detail": "Hold released"}


@resource_router.post("/{resource_id}/price")
async def calculate_price(
    resource_id: uuid.UUID,
    data: PriceCalculateRequest,
    session: AsyncSession = Depends(get_db),
):
    resource = await get_resource(session, resource_id)
    rt = await get_resource_type(session, resource.type_id)
    from app.domains.resources.pricing.strategy import get_pricing_provider
    pricing = get_pricing_provider(rt.pricing_model)
    price = pricing.calculate(resource.base_price, data.start, data.end, rt.pricing_config)
    return {"price": price, "currency": resource.currency}
```

- [ ] **Step 2: Register routers in main.py**

In `backend/app/main.py`, add import:

```python
from app.domains.resources.router import resource_router, resource_type_router
```

Add after `app.include_router(auth_router)`:

```python
app.include_router(resource_type_router)
app.include_router(resource_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/domains/resources/router.py backend/app/main.py
git commit -m "feat(resources): add resource type and resource API routers"
```

---

### Task 9: Test Infrastructure — Admin User Fixture

**Files:**
- Modify: `backend/tests/conftest.py`

Add fixtures for authenticated admin and customer users. Also seed default roles in test_tenant fixture so permission checks work.

- [ ] **Step 1: Update conftest.py**

Add the following imports at the top of `backend/tests/conftest.py`:

```python
from app.core.auth.models import User
from app.core.auth.password import hash_password
from app.core.auth.seed import seed_default_roles
```

Update the `test_tenant` fixture to seed default roles after creating tables:

```python
@pytest.fixture
async def test_tenant(db_session: AsyncSession, db_engine) -> AsyncGenerator[Tenant, None]:
    tenant_id = uuid.uuid4()
    schema_name = f"tenant_test_{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        id=tenant_id,
        name="Test Tenant",
        slug=f"test-{uuid.uuid4().hex[:8]}",
        schema_name=schema_name,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)

    await db_session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
    await db_session.commit()
    await create_tenant_tables(db_engine, schema_name)

    await db_session.execute(text(f"SET search_path TO {schema_name}, public"))
    await seed_default_roles(db_session)
    await db_session.execute(text("SET search_path TO public"))

    set_current_tenant(TenantContext(tenant=tenant, schema_name=schema_name))
    yield tenant
    set_current_tenant(None)

    await db_session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
    await db_session.commit()
```

Add new fixtures after the existing ones:

```python
@pytest.fixture
async def admin_headers(client: AsyncClient, test_tenant: Tenant, db_session: AsyncSession) -> dict:
    schema_name = test_tenant.schema_name
    await db_session.execute(text(f"SET search_path TO {schema_name}, public"))
    admin = User(
        email="admin@test.com",
        password_hash=hash_password("adminpass123"),
        full_name="Test Admin",
        user_type="admin",
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.execute(text("SET search_path TO public"))

    resp = await client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "adminpass123"},
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    tokens = resp.json()
    return {
        "X-Tenant-ID": test_tenant.slug,
        "Authorization": f"Bearer {tokens['access_token']}",
    }


@pytest.fixture
async def customer_headers(client: AsyncClient, test_tenant: Tenant) -> dict:
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "customer@test.com",
            "password": "customerpass1",
            "full_name": "Test Customer",
        },
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    tokens = resp.json()
    return {
        "X-Tenant-ID": test_tenant.slug,
        "Authorization": f"Bearer {tokens['access_token']}",
    }
```

Also add the `AsyncClient` import if not present:

```python
from httpx import ASGITransport, AsyncClient
```

- [ ] **Step 2: Run existing tests to verify no regressions**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: add admin/customer fixtures and seed roles in test_tenant"
```

---

### Task 10: Integration Tests — Resource Types

**Files:**
- Create: `backend/tests/test_resource_integration.py`

Full API flow tests for resource type CRUD and template instantiation.

- [ ] **Step 1: Write resource type integration tests**

Create `backend/tests/test_resource_integration.py`:

```python
import pytest
from httpx import AsyncClient

from app.core.tenancy.models import Tenant


@pytest.mark.asyncio
async def test_create_resource_type(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/resource-types/",
        json={
            "name": "Apartments",
            "slug": "apartments",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
            "attribute_schema": [
                {"name": "bedrooms", "type": "number", "required": True, "filterable": True},
                {"name": "amenities", "type": "tags", "required": False, "filterable": True},
            ],
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Apartments"
    assert data["slug"] == "apartments"
    assert data["availability_model"] == "date_range"
    assert data["is_active"] is True
    assert len(data["attribute_schema"]) == 2


@pytest.mark.asyncio
async def test_create_resource_type_duplicate_slug(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/resource-types/",
        json={
            "name": "Boats",
            "slug": "boats",
            "availability_model": "hourly",
            "pricing_model": "per_hour",
        },
        headers=admin_headers,
    )
    response = await client.post(
        "/api/resource-types/",
        json={
            "name": "Boats Again",
            "slug": "boats",
            "availability_model": "hourly",
            "pricing_model": "per_hour",
        },
        headers=admin_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_resource_type_requires_admin(
    client: AsyncClient, customer_headers: dict
):
    response = await client.post(
        "/api/resource-types/",
        json={
            "name": "Test",
            "slug": "test-no-perm",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
        },
        headers=customer_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_resource_types(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/resource-types/",
        json={
            "name": "Cars",
            "slug": "cars",
            "availability_model": "hourly",
            "pricing_model": "per_hour",
        },
        headers=admin_headers,
    )
    response = await client.get(
        "/api/resource-types/",
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    slugs = [t["slug"] for t in data]
    assert "cars" in slugs


@pytest.mark.asyncio
async def test_get_resource_type_by_slug(client: AsyncClient, admin_headers: dict):
    await client.post(
        "/api/resource-types/",
        json={
            "name": "Villas",
            "slug": "villas",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
        },
        headers=admin_headers,
    )
    response = await client.get(
        "/api/resource-types/villas",
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "villas"


@pytest.mark.asyncio
async def test_update_resource_type(client: AsyncClient, admin_headers: dict):
    create = await client.post(
        "/api/resource-types/",
        json={
            "name": "Offices",
            "slug": "offices",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
        },
        headers=admin_headers,
    )
    rt_id = create.json()["id"]
    response = await client.put(
        f"/api/resource-types/{rt_id}",
        json={"name": "Office Spaces", "icon": "building"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Office Spaces"
    assert response.json()["icon"] == "building"


@pytest.mark.asyncio
async def test_delete_resource_type(client: AsyncClient, admin_headers: dict):
    create = await client.post(
        "/api/resource-types/",
        json={
            "name": "Temp Type",
            "slug": "temp-type",
            "availability_model": "hourly",
            "pricing_model": "per_hour",
        },
        headers=admin_headers,
    )
    rt_id = create.json()["id"]
    response = await client.delete(
        f"/api/resource-types/{rt_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204

    get_resp = await client.get(
        "/api/resource-types/temp-type",
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert get_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_create_from_template(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/resource-types/from-template/venues",
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "venues"
    assert data["availability_model"] == "date_range"
    assert data["pricing_model"] == "fixed_per_day"
    assert data["attribute_schema"] is not None
    assert len(data["attribute_schema"]) >= 4


@pytest.mark.asyncio
async def test_create_from_template_not_found(client: AsyncClient, admin_headers: dict):
    response = await client.post(
        "/api/resource-types/from-template/nonexistent",
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient, test_tenant: Tenant):
    response = await client.get(
        "/api/resource-types/templates",
        headers={"X-Tenant-ID": test_tenant.slug},
    )
    assert response.status_code == 200
    data = response.json()
    assert "venues" in data
    assert "vehicles" in data
    assert "cooks" in data
```

- [ ] **Step 2: Run integration tests**

Run: `cd backend && python -m pytest tests/test_resource_integration.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_resource_integration.py
git commit -m "test(resources): add resource type integration tests with template flows"
```

---

### Task 11: Integration Tests — Resources + Availability

**Files:**
- Modify: `backend/tests/test_resource_integration.py`

Full CRUD for resources plus availability check, hold, release, and pricing calculation.

- [ ] **Step 1: Add resource CRUD tests**

Append to `backend/tests/test_resource_integration.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone


@pytest.fixture
async def venue_type_id(client: AsyncClient, admin_headers: dict) -> str:
    resp = await client.post(
        "/api/resource-types/from-template/venues",
        headers=admin_headers,
    )
    if resp.status_code == 409:
        get_resp = await client.get(
            "/api/resource-types/venues",
            headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
        )
        return get_resp.json()["id"]
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_resource(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    response = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Beach House",
            "description": "Beautiful beachfront property",
            "base_price": 150.0,
            "attributes": {
                "property_type": "house",
                "bedrooms": 3,
                "bathrooms": 2,
                "max_guests": 6,
                "amenities": ["wifi", "pool", "parking"],
            },
            "location_lat": 25.7617,
            "location_lng": -80.1918,
            "location_address": "123 Beach Rd, Miami, FL",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Beach House"
    assert data["base_price"] == 150.0
    assert data["status"] == "draft"
    assert data["attributes"]["bedrooms"] == 3


@pytest.mark.asyncio
async def test_create_resource_invalid_attributes(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    response = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Bad Attrs",
            "base_price": 100.0,
            "attributes": {
                "property_type": "spaceship",
                "bedrooms": "many",
                "bathrooms": 1,
                "max_guests": 4,
            },
        },
        headers=admin_headers,
    )
    assert response.status_code == 422
    assert "attribute_errors" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_resources(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Mountain Cabin",
            "base_price": 200.0,
            "attributes": {
                "property_type": "house",
                "bedrooms": 2,
                "bathrooms": 1,
                "max_guests": 4,
            },
        },
        headers=admin_headers,
    )
    response = await client.get(
        "/api/resources/",
        params={"type_id": venue_type_id},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_update_resource(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    create = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Old Name",
            "base_price": 100.0,
            "attributes": {
                "property_type": "apartment",
                "bedrooms": 1,
                "bathrooms": 1,
                "max_guests": 2,
            },
        },
        headers=admin_headers,
    )
    resource_id = create.json()["id"]
    response = await client.put(
        f"/api/resources/{resource_id}",
        json={"name": "New Name", "base_price": 120.0, "status": "active"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["base_price"] == 120.0
    assert data["status"] == "active"
    assert data["version"] == 2


@pytest.mark.asyncio
async def test_delete_resource(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    create = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Temp Resource",
            "base_price": 50.0,
            "attributes": {
                "property_type": "studio",
                "bedrooms": 0,
                "bathrooms": 1,
                "max_guests": 1,
            },
        },
        headers=admin_headers,
    )
    resource_id = create.json()["id"]
    response = await client.delete(
        f"/api/resources/{resource_id}",
        headers=admin_headers,
    )
    assert response.status_code == 204

    get_resp = await client.get(
        f"/api/resources/{resource_id}",
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert get_resp.json()["status"] == "archived"
```

- [ ] **Step 2: Add availability and pricing tests**

Append to `backend/tests/test_resource_integration.py`:

```python
@pytest.fixture
async def active_venue(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
) -> dict:
    create = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Test Venue",
            "base_price": 100.0,
            "attributes": {
                "property_type": "apartment",
                "bedrooms": 2,
                "bathrooms": 1,
                "max_guests": 4,
            },
        },
        headers=admin_headers,
    )
    resource_id = create.json()["id"]
    await client.put(
        f"/api/resources/{resource_id}",
        json={"status": "active"},
        headers=admin_headers,
    )
    return {"id": resource_id, "base_price": 100.0}


@pytest.mark.asyncio
async def test_check_availability(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    start = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=13)).isoformat()
    response = await client.post(
        f"/api/resources/{active_venue['id']}/availability/check",
        json={"start": start, "end": end},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is True
    assert data["price"] == 300.0


@pytest.mark.asyncio
async def test_hold_resource(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    start = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=22)).isoformat()
    response = await client.post(
        f"/api/resources/{active_venue['id']}/availability/hold",
        json={"start": start, "end": end, "hold_minutes": 10},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "hold_token" in data
    assert data["price"] == 200.0


@pytest.mark.asyncio
async def test_hold_then_check_unavailable(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    start = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=32)).isoformat()

    hold = await client.post(
        f"/api/resources/{active_venue['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    assert hold.status_code == 200

    check = await client.post(
        f"/api/resources/{active_venue['id']}/availability/check",
        json={"start": start, "end": end},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert check.status_code == 200
    assert check.json()["available"] is False


@pytest.mark.asyncio
async def test_hold_then_release_then_available(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    start = (datetime.now(timezone.utc) + timedelta(days=40)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=42)).isoformat()

    hold = await client.post(
        f"/api/resources/{active_venue['id']}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    token = hold.json()["hold_token"]

    release = await client.post(
        f"/api/resources/{active_venue['id']}/availability/release",
        json={"hold_token": token},
        headers=admin_headers,
    )
    assert release.status_code == 200

    check = await client.post(
        f"/api/resources/{active_venue['id']}/availability/check",
        json={"start": start, "end": end},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert check.json()["available"] is True


@pytest.mark.asyncio
async def test_calculate_price(
    client: AsyncClient, admin_headers: dict, active_venue: dict
):
    start = (datetime.now(timezone.utc) + timedelta(days=50)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=55)).isoformat()
    response = await client.post(
        f"/api/resources/{active_venue['id']}/price",
        json={"start": start, "end": end},
        headers={"X-Tenant-ID": admin_headers["X-Tenant-ID"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 500.0
    assert data["currency"] == "USD"


@pytest.mark.asyncio
async def test_hold_inactive_resource_fails(
    client: AsyncClient, admin_headers: dict, venue_type_id: str
):
    create = await client.post(
        "/api/resources/",
        json={
            "type_id": venue_type_id,
            "name": "Inactive Place",
            "base_price": 75.0,
            "attributes": {
                "property_type": "apartment",
                "bedrooms": 1,
                "bathrooms": 1,
                "max_guests": 2,
            },
        },
        headers=admin_headers,
    )
    resource_id = create.json()["id"]
    start = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=62)).isoformat()
    response = await client.post(
        f"/api/resources/{resource_id}/availability/hold",
        json={"start": start, "end": end},
        headers=admin_headers,
    )
    assert response.status_code == 400
```

- [ ] **Step 3: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS (auth + resource)

- [ ] **Step 4: Run linter**

Run: `cd backend && python -m ruff check app/ tests/`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_resource_integration.py
git commit -m "test(resources): add resource CRUD, availability, and pricing integration tests"
```

---

### Task 12: Final Verification + Cleanup

- [ ] **Step 1: Run full test suite**

Run: `cd backend && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Verify linter is clean**

Run: `cd backend && python -m ruff check app/ tests/`
Expected: No errors

- [ ] **Step 3: Verify imports are correct**

Run: `cd backend && python -c "from app.domains.resources.models import ResourceType, Resource, ResourceAvailability; from app.domains.resources.service import create_resource_type, create_resource; from app.domains.resources.availability.strategy import get_availability_provider; from app.domains.resources.pricing.strategy import get_pricing_provider; print('All imports OK')"`
Expected: `All imports OK`

- [ ] **Step 4: Verify tenant provisioning includes resource tables**

Run: `cd backend && python -c "from app.core.tenancy.provisioning import TENANT_TABLE_REGISTRY; print(TENANT_TABLE_REGISTRY)"`
Expected: Output includes `resource_types`, `resources`, `resource_availability`

- [ ] **Step 5: Final commit if any unstaged changes**

```bash
git status
```

Expected: clean working tree

---

## Summary

| Task | Component | Files | Dependencies |
|------|-----------|-------|-------------|
| 1 | Domain package + models | models.py, provisioning.py, env.py | None |
| 2 | Attribute validation | attributes.py | None |
| 3 | Availability protocol + date_range | strategy.py, date_range.py | Task 1 |
| 4 | Time slot + hourly providers | time_slot.py, hourly.py | Task 3 |
| 5 | Pricing protocol + providers | pricing/strategy.py, providers.py | None |
| 6 | Schemas + service | schemas.py, service.py | Tasks 1-5 |
| 7 | Pre-built templates | templates.py | None |
| 8 | Router (types + resources) | router.py, main.py | Tasks 6, 7 |
| 9 | Test infrastructure | conftest.py | None |
| 10 | Integration tests — types | test_resource_integration.py | Tasks 8, 9 |
| 11 | Integration tests — resources + availability | test_resource_integration.py | Task 10 |
| 12 | Final verification | — | All |

**Parallel execution opportunities:**
- Tasks 1, 2, 5, 7 are independent — can run in parallel
- Tasks 3, 4 depend on Task 1
- Task 6 depends on Tasks 1-5
- Task 8 depends on Tasks 6, 7
- Task 9 is independent
- Tasks 10, 11 depend on Tasks 8, 9
- Task 12 depends on all

---

## Not In Scope (Future Plans)

- **Meilisearch index sync** — Auto-creating search indexes when resource types are created. Deferred to Plan 5 (Search & Discovery).
- **Image/file uploads for resources** — MinIO integration for resource photos. Deferred to a storage plan.
- **Bulk resource import** — CSV/JSON import for listers. Post-MVP.
- **Resource versioning history** — Audit trail of changes. Deferred to audit log plan.
- **Custom pricing rules engine** — The `custom` pricing model from the spec. Post-MVP.
