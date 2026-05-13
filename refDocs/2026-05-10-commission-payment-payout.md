# Commission, Payment & Payout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add commission tracking (resource-type default + per-resource override), payment processing (manual now, Stripe/Razorpay scaffolded), payout settlement, admin-on-behalf booking, and staff disable cascade.

**Architecture:** Commission config stored as JSONB on ResourceType and Resource models. Payment abstracted behind a provider protocol (Manual ships first). Payouts are admin-triggered settlements. All new tables live in per-tenant schemas. Frontend uses existing shadcn/Card pattern for settings pages.

**Tech Stack:** FastAPI, SQLModel, PostgreSQL (JSONB), Celery, React 19, TanStack Query, Zustand, shadcn/ui, Zod

---

## File Map

### Backend — New Files

| File | Responsibility |
|------|---------------|
| `backend/app/core/commission/schemas.py` | CommissionConfig Pydantic model, calculation request/response |
| `backend/app/core/commission/service.py` | resolve_commission(), calculate_breakdown() |
| `backend/app/core/commission/router.py` | Commission CRUD endpoints (admin-only) |
| `backend/app/core/payments/__init__.py` | Empty init |
| `backend/app/core/payments/models.py` | Payment SQLModel |
| `backend/app/core/payments/schemas.py` | PaymentResponse, MarkPaidRequest |
| `backend/app/core/payments/provider.py` | PaymentProvider protocol + get_provider() factory |
| `backend/app/core/payments/providers/__init__.py` | Empty init |
| `backend/app/core/payments/providers/manual.py` | ManualProvider |
| `backend/app/core/payments/providers/stripe.py` | StripeProvider (scaffolded) |
| `backend/app/core/payments/providers/razorpay.py` | RazorpayProvider (scaffolded) |
| `backend/app/core/payments/service.py` | Payment lifecycle (create, mark_paid, refund) |
| `backend/app/core/payments/router.py` | Payment endpoints |
| `backend/app/core/payouts/__init__.py` | Empty init |
| `backend/app/core/payouts/models.py` | Payout + PayoutItem SQLModels |
| `backend/app/core/payouts/schemas.py` | Payout request/response schemas |
| `backend/app/core/payouts/service.py` | Payout creation, settlement, balance queries |
| `backend/app/core/payouts/router.py` | Payout endpoints |
| `backend/tests/test_commission_unit.py` | Commission calculation unit tests |
| `backend/tests/test_payment_unit.py` | Payment model + manual provider tests |
| `backend/tests/test_payout_unit.py` | Payout model tests |

### Backend — Modified Files

| File | Change |
|------|--------|
| `backend/app/domains/resources/models.py` | Add `commission_config` JSONB to ResourceType + Resource, add `suspension_reason` to Resource |
| `backend/app/domains/bookings/models.py` | Add `service_fee`, `platform_commission`, `owner_payout`, `customer_total` fields |
| `backend/app/domains/bookings/schemas.py` | Add `user_id` to BookingCreate, commission fields to BookingResponse |
| `backend/app/domains/bookings/service.py` | Commission calculation on create, admin booking for-customer logic |
| `backend/app/domains/resources/service.py` | Default `status=active` filter when no status provided |
| `backend/app/core/admin/router.py` | Add activate endpoint, impact-check endpoint |
| `backend/app/core/admin/service.py` | Cascade deactivate/activate logic |
| `backend/app/core/admin/schemas.py` | Add DeactivationImpactResponse |
| `backend/app/core/tenancy/middleware.py` | Add payment webhook to TENANT_FREE_PREFIXES |
| `backend/app/main.py` | Register commission, payment, payout routers |

### Frontend — New Files

| File | Responsibility |
|------|---------------|
| `frontend/src/app/admin/settings/commission/page.tsx` | Commission settings page |
| `frontend/src/app/admin/settings/payments/page.tsx` | Payment gateway settings page |
| `frontend/src/app/admin/payouts/page.tsx` | Payout management page |
| `frontend/src/types/commission.ts` | Commission TypeScript types |
| `frontend/src/types/payment.ts` | Payment TypeScript types |
| `frontend/src/types/payout.ts` | Payout TypeScript types |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `frontend/src/components/shell/icon-rail.tsx` | Add Payouts nav item |
| `frontend/src/components/shell/sub-nav.tsx` | Add commission + payments sub-nav under Settings, add Payouts section |
| `frontend/src/components/bookings/booking-actions.tsx` | Add "Mark Paid" button |
| `frontend/src/app/admin/bookings/[id]/page.tsx` | Show payment status + commission breakdown |
| `frontend/src/types/api.ts` | Add commission fields to BookingResponse, user_id to BookingCreate |

---

## Task 1: Commission Config Schema + Calculation Service

**Files:**
- Create: `backend/app/core/commission/__init__.py`
- Create: `backend/app/core/commission/schemas.py`
- Create: `backend/app/core/commission/service.py`
- Create: `backend/tests/test_commission_unit.py`

- [ ] **Step 1: Create commission directory**

```bash
mkdir -p backend/app/core/commission
touch backend/app/core/commission/__init__.py
```

- [ ] **Step 2: Write commission unit tests**

Create `backend/tests/test_commission_unit.py`:

```python
from app.core.commission.schemas import CommissionConfig
from app.core.commission.service import calculate_breakdown


def test_calculate_breakdown_percentage_only():
    config = CommissionConfig(
        owner_percent=5.0,
        owner_fixed=0.0,
        customer_percent=3.0,
        customer_fixed=0.0,
    )
    result = calculate_breakdown(1000.0, "INR", config)
    assert result["platform_commission"] == 50.0  # 5% of 1000
    assert result["service_fee"] == 30.0  # 3% of 1000
    assert result["owner_payout"] == 950.0  # 1000 - 50
    assert result["customer_total"] == 1030.0  # 1000 + 30


def test_calculate_breakdown_with_fixed_fees():
    config = CommissionConfig(
        owner_percent=5.0,
        owner_fixed=25.0,
        customer_percent=3.0,
        customer_fixed=50.0,
    )
    result = calculate_breakdown(1000.0, "INR", config)
    assert result["platform_commission"] == 75.0  # (5% of 1000) + 25
    assert result["service_fee"] == 80.0  # (3% of 1000) + 50
    assert result["owner_payout"] == 925.0  # 1000 - 75
    assert result["customer_total"] == 1080.0  # 1000 + 80


def test_calculate_breakdown_zero_config():
    config = CommissionConfig()
    result = calculate_breakdown(500.0, "USD", config)
    assert result["platform_commission"] == 0.0
    assert result["service_fee"] == 0.0
    assert result["owner_payout"] == 500.0
    assert result["customer_total"] == 500.0


def test_calculate_breakdown_none_config():
    result = calculate_breakdown(500.0, "USD", None)
    assert result["platform_commission"] == 0.0
    assert result["service_fee"] == 0.0
    assert result["owner_payout"] == 500.0
    assert result["customer_total"] == 500.0


def test_commission_config_defaults():
    config = CommissionConfig()
    assert config.owner_percent == 0.0
    assert config.owner_fixed == 0.0
    assert config.customer_percent == 0.0
    assert config.customer_fixed == 0.0
    assert config.currency == "USD"


def test_commission_config_from_dict():
    data = {
        "owner_percent": 10.0,
        "customer_percent": 5.0,
        "customer_fixed": 100.0,
        "currency": "INR",
    }
    config = CommissionConfig(**data)
    assert config.owner_percent == 10.0
    assert config.owner_fixed == 0.0
    assert config.customer_fixed == 100.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_commission_unit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.commission'`

- [ ] **Step 4: Create commission schemas**

Create `backend/app/core/commission/schemas.py`:

```python
import uuid

from pydantic import BaseModel


class CommissionConfig(BaseModel):
    owner_percent: float = 0.0
    owner_fixed: float = 0.0
    customer_percent: float = 0.0
    customer_fixed: float = 0.0
    currency: str = "USD"


class CommissionBreakdown(BaseModel):
    total_price: float
    service_fee: float
    platform_commission: float
    owner_payout: float
    customer_total: float


class CommissionConfigUpdate(BaseModel):
    owner_percent: float | None = None
    owner_fixed: float | None = None
    customer_percent: float | None = None
    customer_fixed: float | None = None
    currency: str | None = None


class CommissionConfigResponse(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    config: CommissionConfig | None
    inherited_from: str | None
```

- [ ] **Step 5: Create commission service**

Create `backend/app/core/commission/service.py`:

```python
import uuid

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.commission.schemas import CommissionConfig
from app.domains.resources.models import Resource, ResourceType


def calculate_breakdown(
    total_price: float,
    currency: str,
    config: CommissionConfig | None,
) -> dict:
    if config is None:
        return {
            "service_fee": 0.0,
            "platform_commission": 0.0,
            "owner_payout": total_price,
            "customer_total": total_price,
        }

    platform_commission = round(
        (total_price * config.owner_percent / 100) + config.owner_fixed, 2
    )
    service_fee = round(
        (total_price * config.customer_percent / 100) + config.customer_fixed, 2
    )
    owner_payout = round(total_price - platform_commission, 2)
    customer_total = round(total_price + service_fee, 2)

    return {
        "service_fee": service_fee,
        "platform_commission": platform_commission,
        "owner_payout": owner_payout,
        "customer_total": customer_total,
    }


async def resolve_commission(
    session: AsyncSession,
    resource_id: uuid.UUID,
) -> CommissionConfig | None:
    result = await session.exec(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    if resource.commission_config:
        return CommissionConfig(**resource.commission_config)

    result = await session.exec(
        select(ResourceType).where(ResourceType.id == resource.type_id)
    )
    resource_type = result.first()
    if resource_type and resource_type.commission_config:
        return CommissionConfig(**resource_type.commission_config)

    return None
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_commission_unit.py -v`
Expected: All 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/commission/ backend/tests/test_commission_unit.py
git commit -m "feat(commission): add commission config schema and calculation service"
```

---

## Task 2: Add commission_config to ResourceType + Resource Models

**Files:**
- Modify: `backend/app/domains/resources/models.py:15-66`

- [ ] **Step 1: Add commission_config to ResourceType**

In `backend/app/domains/resources/models.py`, after the `cancellation_defaults` field (line 28), add:

```python
    commission_config: dict | None = Field(default=None, sa_column=Column(JSONB))
```

- [ ] **Step 2: Add commission_config and suspension_reason to Resource**

In the same file, after the `owner_id` field (line 57), add:

```python
    commission_config: dict | None = Field(default=None, sa_column=Column(JSONB))
    suspension_reason: str | None = Field(default=None, max_length=50)
```

- [ ] **Step 3: Update TENANT_RESOURCE_TABLES if needed**

No change needed — tables are already tracked. The new columns are on existing tables.

- [ ] **Step 4: Verify models load**

Run: `cd backend && python -c "from app.domains.resources.models import ResourceType, Resource; print('OK')"` (may fail due to missing slowapi in local env — that's OK, verify import chain is correct)

- [ ] **Step 5: Commit**

```bash
git add backend/app/domains/resources/models.py
git commit -m "feat(models): add commission_config to ResourceType and Resource, suspension_reason to Resource"
```

---

## Task 3: Commission Router (Admin CRUD)

**Files:**
- Create: `backend/app/core/commission/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create commission router**

Create `backend/app/core/commission/router.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import require_permission
from app.core.auth.models import User
from app.core.commission.schemas import (
    CommissionConfig,
    CommissionConfigResponse,
    CommissionConfigUpdate,
)
from app.core.commission.service import calculate_breakdown, resolve_commission
from app.database import get_db
from app.domains.resources.models import Resource, ResourceType

router = APIRouter(prefix="/api/commission", tags=["commission"])


def _require_admin():
    return require_permission("*:*:*")


@router.get("/resource-type/{resource_type_id}", response_model=CommissionConfigResponse)
async def get_resource_type_commission(
    resource_type_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    result = await session.exec(
        select(ResourceType).where(ResourceType.id == resource_type_id)
    )
    rt = result.first()
    if rt is None:
        raise HTTPException(status_code=404, detail="Resource type not found")
    config = CommissionConfig(**rt.commission_config) if rt.commission_config else None
    return CommissionConfigResponse(
        entity_type="resource_type",
        entity_id=rt.id,
        config=config,
        inherited_from=None,
    )


@router.patch("/resource-type/{resource_type_id}", response_model=CommissionConfigResponse)
async def update_resource_type_commission(
    resource_type_id: uuid.UUID,
    data: CommissionConfigUpdate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    result = await session.exec(
        select(ResourceType).where(ResourceType.id == resource_type_id)
    )
    rt = result.first()
    if rt is None:
        raise HTTPException(status_code=404, detail="Resource type not found")

    existing = CommissionConfig(**(rt.commission_config or {}))
    updates = data.model_dump(exclude_none=True)
    merged = existing.model_copy(update=updates)
    rt.commission_config = merged.model_dump()
    session.add(rt)
    await session.commit()
    await session.refresh(rt)

    return CommissionConfigResponse(
        entity_type="resource_type",
        entity_id=rt.id,
        config=merged,
        inherited_from=None,
    )


@router.get("/resource/{resource_id}", response_model=CommissionConfigResponse)
async def get_resource_commission(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    result = await session.exec(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    if resource.commission_config:
        config = CommissionConfig(**resource.commission_config)
        return CommissionConfigResponse(
            entity_type="resource",
            entity_id=resource.id,
            config=config,
            inherited_from=None,
        )

    result = await session.exec(
        select(ResourceType).where(ResourceType.id == resource.type_id)
    )
    rt = result.first()
    if rt and rt.commission_config:
        config = CommissionConfig(**rt.commission_config)
        return CommissionConfigResponse(
            entity_type="resource",
            entity_id=resource.id,
            config=config,
            inherited_from="resource_type",
        )

    return CommissionConfigResponse(
        entity_type="resource",
        entity_id=resource.id,
        config=None,
        inherited_from=None,
    )


@router.patch("/resource/{resource_id}", response_model=CommissionConfigResponse)
async def update_resource_commission(
    resource_id: uuid.UUID,
    data: CommissionConfigUpdate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    result = await session.exec(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")

    existing = CommissionConfig(**(resource.commission_config or {}))
    updates = data.model_dump(exclude_none=True)
    merged = existing.model_copy(update=updates)
    resource.commission_config = merged.model_dump()
    session.add(resource)
    await session.commit()
    await session.refresh(resource)

    return CommissionConfigResponse(
        entity_type="resource",
        entity_id=resource.id,
        config=merged,
        inherited_from=None,
    )


@router.delete("/resource/{resource_id}", status_code=204)
async def delete_resource_commission(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    result = await session.exec(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    resource.commission_config = None
    session.add(resource)
    await session.commit()


@router.get("/preview")
async def preview_commission(
    resource_id: uuid.UUID,
    amount: float = 1000.0,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    config = await resolve_commission(session, resource_id)
    result = await session.exec(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.first()
    currency = resource.currency if resource else "USD"
    breakdown = calculate_breakdown(amount, currency, config)
    return {
        "amount": amount,
        "currency": currency,
        "config": config.model_dump() if config else None,
        **breakdown,
    }
```

- [ ] **Step 2: Register commission router in main.py**

In `backend/app/main.py`, add import after line 14:

```python
from app.core.commission.router import router as commission_router
```

Add after `app.include_router(currency_router)` (line 103):

```python
app.include_router(commission_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/commission/router.py backend/app/main.py
git commit -m "feat(commission): add commission CRUD router with preview endpoint"
```

---

## Task 4: Integrate Commission into Booking Creation

**Files:**
- Modify: `backend/app/domains/bookings/models.py`
- Modify: `backend/app/domains/bookings/schemas.py`
- Modify: `backend/app/domains/bookings/service.py:74-142`

- [ ] **Step 1: Add commission fields to Booking model**

In `backend/app/domains/bookings/models.py`, after the `currency` field (line 21), add:

```python
    service_fee: float = Field(default=0.0)
    platform_commission: float = Field(default=0.0)
    owner_payout: float = Field(default=0.0)
    customer_total: float = Field(default=0.0)
```

- [ ] **Step 2: Add user_id to BookingCreate, commission fields to BookingResponse**

In `backend/app/domains/bookings/schemas.py`, add `user_id` to `BookingCreate`:

```python
class BookingCreate(BaseModel):
    resource_id: uuid.UUID
    hold_token: str
    start_time: datetime
    end_time: datetime
    notes: str | None = None
    auto_confirm: bool = True
    user_id: uuid.UUID | None = None
```

Add commission fields to `BookingResponse` after the `currency` field:

```python
    service_fee: float
    platform_commission: float
    owner_payout: float
    customer_total: float
```

- [ ] **Step 3: Update create_booking in service.py**

In `backend/app/domains/bookings/service.py`, add import at top:

```python
from app.core.commission.service import calculate_breakdown, resolve_commission
```

Replace the booking creation block in `create_booking()` (lines 95-114). After `total_price` is calculated (line 98), add commission resolution and calculation. The full updated function body from line 95 onward:

```python
    commission_config = await resolve_commission(session, data.resource_id)
    breakdown = calculate_breakdown(total_price, resource.currency, commission_config)

    cancellation_policy = resource_type.cancellation_defaults

    booking = Booking(
        resource_id=data.resource_id,
        user_id=user_id,
        status="pending",
        start_time=data.start_time,
        end_time=data.end_time,
        total_price=total_price,
        currency=resource.currency,
        service_fee=breakdown["service_fee"],
        platform_commission=breakdown["platform_commission"],
        owner_payout=breakdown["owner_payout"],
        customer_total=breakdown["customer_total"],
        hold_token=data.hold_token,
        cancellation_policy=cancellation_policy,
        notes=data.notes,
        auto_confirm=data.auto_confirm,
    )
```

- [ ] **Step 4: Add admin booking-for-customer logic**

In `backend/app/domains/bookings/service.py`, update the `create_booking` function signature to accept `is_admin`:

```python
async def create_booking(
    session: AsyncSession,
    data: BookingCreate,
    user_id: uuid.UUID,
    is_admin: bool = False,
) -> Booking:
```

After the resource/type validation, before pricing, add:

```python
    booking_user_id = user_id
    if data.user_id is not None:
        if not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Only admins can book on behalf of another user",
            )
        booking_user_id = data.user_id
```

Then change the `Booking(user_id=user_id, ...)` to `Booking(user_id=booking_user_id, ...)` and update the email dispatch to use `booking_user_id`.

- [ ] **Step 5: Update booking router to pass is_admin**

In `backend/app/domains/bookings/router.py`, update the `create_booking_endpoint`:

```python
@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking_endpoint(
    data: BookingCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await create_booking(
        session, data, user.id,
        is_admin=(user.user_type == "admin"),
    )
```

- [ ] **Step 6: Update booking unit tests**

Add to `backend/tests/test_booking_unit.py`:

```python
def test_booking_model_commission_defaults():
    b = Booking(
        resource_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(days=1),
        total_price=100.0,
    )
    assert b.service_fee == 0.0
    assert b.platform_commission == 0.0
    assert b.owner_payout == 0.0
    assert b.customer_total == 0.0


def test_booking_create_schema_with_user_id():
    data = BookingCreate(
        resource_id=uuid.uuid4(),
        hold_token="tok-123",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(days=1),
        user_id=uuid.uuid4(),
    )
    assert data.user_id is not None


def test_booking_create_schema_without_user_id():
    data = BookingCreate(
        resource_id=uuid.uuid4(),
        hold_token="tok-123",
        start_time=datetime.now(UTC),
        end_time=datetime.now(UTC) + timedelta(days=1),
    )
    assert data.user_id is None
```

- [ ] **Step 7: Run tests**

Run: `cd backend && python -m pytest tests/test_booking_unit.py tests/test_commission_unit.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/domains/bookings/ backend/tests/test_booking_unit.py
git commit -m "feat(bookings): integrate commission calculation and admin-on-behalf booking"
```

---

## Task 5: Payment Model + Manual Provider

**Files:**
- Create: `backend/app/core/payments/__init__.py`
- Create: `backend/app/core/payments/models.py`
- Create: `backend/app/core/payments/schemas.py`
- Create: `backend/app/core/payments/provider.py`
- Create: `backend/app/core/payments/providers/__init__.py`
- Create: `backend/app/core/payments/providers/manual.py`
- Create: `backend/tests/test_payment_unit.py`

- [ ] **Step 1: Create payment directories**

```bash
mkdir -p backend/app/core/payments/providers
touch backend/app/core/payments/__init__.py
touch backend/app/core/payments/providers/__init__.py
```

- [ ] **Step 2: Write payment unit tests**

Create `backend/tests/test_payment_unit.py`:

```python
import uuid
from datetime import UTC, datetime, timedelta

from app.core.payments.models import Payment, TENANT_PAYMENT_TABLES


def test_payment_model_defaults():
    p = Payment(
        booking_id=uuid.uuid4(),
        amount=1000.0,
        currency="INR",
        provider="manual",
    )
    assert p.status == "pending"
    assert p.provider_ref is None
    assert p.paid_at is None
    assert p.refund_amount is None


def test_payment_valid_statuses():
    valid = {"pending", "paid", "failed", "refunded", "partially_refunded"}
    for s in valid:
        p = Payment(
            booking_id=uuid.uuid4(),
            amount=100.0,
            currency="USD",
            provider="manual",
            status=s,
        )
        assert p.status == s


def test_tenant_payment_tables():
    assert "payments" in TENANT_PAYMENT_TABLES
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_payment_unit.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Create Payment model**

Create `backend/app/core/payments/models.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

TENANT_PAYMENT_TABLES: set[str] = {"payments"}


class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", index=True)
    amount: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=10)
    provider: str = Field(default="manual", max_length=20)
    status: str = Field(default="pending", max_length=30)
    provider_ref: str | None = Field(default=None, max_length=255)
    provider_data: dict | None = Field(default=None, sa_column=Column(JSONB))
    paid_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    refund_amount: float | None = Field(default=None)
    refunded_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
```

- [ ] **Step 5: Create payment schemas**

Create `backend/app/core/payments/schemas.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class PaymentResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: float
    currency: str
    provider: str
    status: str
    provider_ref: str | None
    paid_at: datetime | None
    refund_amount: float | None
    refunded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MarkPaidRequest(BaseModel):
    notes: str | None = None


class RefundRequest(BaseModel):
    amount: float | None = None
    reason: str | None = None
```

- [ ] **Step 6: Create payment provider protocol**

Create `backend/app/core/payments/provider.py`:

```python
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class PaymentResult(BaseModel):
    success: bool
    provider_ref: str | None = None
    provider_data: dict | None = None
    error: str | None = None


class RefundResult(BaseModel):
    success: bool
    refund_ref: str | None = None
    error: str | None = None


class PaymentProvider(Protocol):
    async def create_payment(
        self, amount: float, currency: str, metadata: dict
    ) -> PaymentResult: ...

    async def confirm_payment(self, provider_ref: str) -> PaymentResult: ...

    async def refund_payment(
        self, provider_ref: str, amount: float
    ) -> RefundResult: ...

    async def verify_keys(self, config: dict) -> bool: ...


def get_provider(provider_name: str, config: dict | None = None) -> PaymentProvider:
    if provider_name == "stripe":
        from app.core.payments.providers.stripe import StripeProvider
        return StripeProvider(config or {})
    elif provider_name == "razorpay":
        from app.core.payments.providers.razorpay import RazorpayProvider
        return RazorpayProvider(config or {})
    else:
        from app.core.payments.providers.manual import ManualProvider
        return ManualProvider()
```

- [ ] **Step 7: Create ManualProvider**

Create `backend/app/core/payments/providers/manual.py`:

```python
from app.core.payments.provider import PaymentResult, RefundResult


class ManualProvider:
    async def create_payment(
        self, amount: float, currency: str, metadata: dict
    ) -> PaymentResult:
        return PaymentResult(success=True, provider_ref=None)

    async def confirm_payment(self, provider_ref: str) -> PaymentResult:
        return PaymentResult(success=True, provider_ref=provider_ref)

    async def refund_payment(
        self, provider_ref: str, amount: float
    ) -> RefundResult:
        return RefundResult(success=True, refund_ref=None)

    async def verify_keys(self, config: dict) -> bool:
        return True
```

- [ ] **Step 8: Run tests**

Run: `cd backend && python -m pytest tests/test_payment_unit.py -v`
Expected: All 3 tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/core/payments/ backend/tests/test_payment_unit.py
git commit -m "feat(payments): add Payment model, provider protocol, and ManualProvider"
```

---

## Task 6: Payment Service + Router

**Files:**
- Create: `backend/app/core/payments/service.py`
- Create: `backend/app/core/payments/router.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/tenancy/middleware.py`

- [ ] **Step 1: Create payment service**

Create `backend/app/core/payments/service.py`:

```python
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.payments.models import Payment
from app.core.payments.provider import get_provider
from app.core.tenancy.context import get_current_tenant
from app.domains.bookings.models import Booking


def _get_payment_config() -> tuple[str, dict]:
    ctx = get_current_tenant()
    config = ctx.tenant.config or {}
    provider_name = config.get("payment_provider", "manual")
    return provider_name, config


async def create_payment_for_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
) -> Payment:
    result = await session.exec(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = result.first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    existing = await session.exec(
        select(Payment).where(Payment.booking_id == booking_id)
    )
    if existing.first() is not None:
        raise HTTPException(status_code=409, detail="Payment already exists for this booking")

    provider_name, config = _get_payment_config()
    provider = get_provider(provider_name, config)

    result_data = await provider.create_payment(
        amount=booking.customer_total,
        currency=booking.currency,
        metadata={"booking_id": str(booking_id)},
    )

    payment = Payment(
        booking_id=booking_id,
        amount=booking.customer_total,
        currency=booking.currency,
        provider=provider_name,
        status="pending" if result_data.success else "failed",
        provider_ref=result_data.provider_ref,
        provider_data=result_data.provider_data,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment_for_booking(
    session: AsyncSession,
    booking_id: uuid.UUID,
) -> Payment | None:
    result = await session.exec(
        select(Payment).where(Payment.booking_id == booking_id)
    )
    return result.first()


async def mark_payment_paid(
    session: AsyncSession,
    payment_id: uuid.UUID,
) -> Payment:
    result = await session.exec(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != "pending":
        raise HTTPException(
            status_code=409, detail=f"Cannot mark as paid: status is '{payment.status}'"
        )

    payment.status = "paid"
    payment.paid_at = datetime.now(UTC)
    payment.updated_at = datetime.now(UTC)
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def refund_payment(
    session: AsyncSession,
    payment_id: uuid.UUID,
    amount: float | None = None,
) -> Payment:
    result = await session.exec(
        select(Payment).where(Payment.id == payment_id)
    )
    payment = result.first()
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != "paid":
        raise HTTPException(
            status_code=409, detail=f"Cannot refund: status is '{payment.status}'"
        )

    refund_amount = amount if amount is not None else payment.amount
    if refund_amount > payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds payment amount")

    provider_name, config = _get_payment_config()
    provider = get_provider(provider_name, config)

    if payment.provider_ref:
        await provider.refund_payment(payment.provider_ref, refund_amount)

    payment.refund_amount = refund_amount
    payment.refunded_at = datetime.now(UTC)
    payment.status = "refunded" if refund_amount >= payment.amount else "partially_refunded"
    payment.updated_at = datetime.now(UTC)
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment
```

- [ ] **Step 2: Create payment router**

Create `backend/app/core/payments/router.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user, require_permission
from app.core.auth.models import User
from app.core.payments.schemas import MarkPaidRequest, PaymentResponse, RefundRequest
from app.core.payments.service import (
    create_payment_for_booking,
    get_payment_for_booking,
    mark_payment_paid,
    refund_payment,
)
from app.database import get_db

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _require_admin():
    return require_permission("*:*:*")


@router.post("/booking/{booking_id}", response_model=PaymentResponse, status_code=201)
async def create_payment(
    booking_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await create_payment_for_booking(session, booking_id)


@router.get("/booking/{booking_id}", response_model=PaymentResponse | None)
async def get_payment(
    booking_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    payment = await get_payment_for_booking(session, booking_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="No payment found for this booking")
    return payment


@router.post("/{payment_id}/mark-paid", response_model=PaymentResponse)
async def mark_paid(
    payment_id: uuid.UUID,
    data: MarkPaidRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    return await mark_payment_paid(session, payment_id)


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def process_refund(
    payment_id: uuid.UUID,
    data: RefundRequest | None = None,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    amount = data.amount if data else None
    return await refund_payment(session, payment_id, amount)
```

- [ ] **Step 3: Register payment router in main.py**

In `backend/app/main.py`, add import:

```python
from app.core.payments.router import router as payment_router
```

Add after `app.include_router(commission_router)`:

```python
app.include_router(payment_router)
```

- [ ] **Step 4: Add payment webhooks to tenant-free prefixes**

In `backend/app/core/tenancy/middleware.py`, add to `TENANT_FREE_PREFIXES`:

```python
TENANT_FREE_PREFIXES = ("/api/platform/", "/api/health/", "/api/currency/", "/api/payments/webhook/")
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/payments/service.py backend/app/core/payments/router.py backend/app/main.py backend/app/core/tenancy/middleware.py
git commit -m "feat(payments): add payment service, router, and webhook tenant-free path"
```

---

## Task 7: Stripe + Razorpay Provider Scaffolds

**Files:**
- Create: `backend/app/core/payments/providers/stripe.py`
- Create: `backend/app/core/payments/providers/razorpay.py`

- [ ] **Step 1: Create StripeProvider scaffold**

Create `backend/app/core/payments/providers/stripe.py`:

```python
import logging

from app.core.payments.provider import PaymentResult, RefundResult

logger = logging.getLogger(__name__)


class StripeProvider:
    def __init__(self, config: dict):
        self.secret_key = config.get("stripe_secret_key", "")
        self.publishable_key = config.get("stripe_publishable_key", "")

    async def create_payment(
        self, amount: float, currency: str, metadata: dict
    ) -> PaymentResult:
        if not self.secret_key:
            return PaymentResult(success=False, error="Stripe secret key not configured")
        try:
            import stripe
            stripe.api_key = self.secret_key
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency=currency.lower(),
                metadata=metadata,
            )
            return PaymentResult(
                success=True,
                provider_ref=intent.id,
                provider_data={"client_secret": intent.client_secret},
            )
        except Exception as e:
            logger.error("Stripe create_payment failed: %s", e)
            return PaymentResult(success=False, error=str(e))

    async def confirm_payment(self, provider_ref: str) -> PaymentResult:
        try:
            import stripe
            stripe.api_key = self.secret_key
            intent = stripe.PaymentIntent.retrieve(provider_ref)
            return PaymentResult(
                success=intent.status == "succeeded",
                provider_ref=provider_ref,
                provider_data={"status": intent.status},
            )
        except Exception as e:
            logger.error("Stripe confirm_payment failed: %s", e)
            return PaymentResult(success=False, error=str(e))

    async def refund_payment(
        self, provider_ref: str, amount: float
    ) -> RefundResult:
        try:
            import stripe
            stripe.api_key = self.secret_key
            refund = stripe.Refund.create(
                payment_intent=provider_ref,
                amount=int(amount * 100),
            )
            return RefundResult(success=True, refund_ref=refund.id)
        except Exception as e:
            logger.error("Stripe refund failed: %s", e)
            return RefundResult(success=False, error=str(e))

    async def verify_keys(self, config: dict) -> bool:
        try:
            import stripe
            stripe.api_key = config.get("stripe_secret_key", "")
            stripe.Account.retrieve()
            return True
        except Exception:
            return False
```

- [ ] **Step 2: Create RazorpayProvider scaffold**

Create `backend/app/core/payments/providers/razorpay.py`:

```python
import logging

from app.core.payments.provider import PaymentResult, RefundResult

logger = logging.getLogger(__name__)


class RazorpayProvider:
    def __init__(self, config: dict):
        self.key_id = config.get("razorpay_key_id", "")
        self.key_secret = config.get("razorpay_key_secret", "")

    def _get_client(self):
        import razorpay
        return razorpay.Client(auth=(self.key_id, self.key_secret))

    async def create_payment(
        self, amount: float, currency: str, metadata: dict
    ) -> PaymentResult:
        if not self.key_id or not self.key_secret:
            return PaymentResult(success=False, error="Razorpay keys not configured")
        try:
            client = self._get_client()
            order = client.order.create({
                "amount": int(amount * 100),
                "currency": currency.upper(),
                "notes": metadata,
            })
            return PaymentResult(
                success=True,
                provider_ref=order["id"],
                provider_data={"order_id": order["id"]},
            )
        except Exception as e:
            logger.error("Razorpay create_payment failed: %s", e)
            return PaymentResult(success=False, error=str(e))

    async def confirm_payment(self, provider_ref: str) -> PaymentResult:
        try:
            client = self._get_client()
            order = client.order.fetch(provider_ref)
            return PaymentResult(
                success=order["status"] == "paid",
                provider_ref=provider_ref,
                provider_data={"status": order["status"]},
            )
        except Exception as e:
            logger.error("Razorpay confirm_payment failed: %s", e)
            return PaymentResult(success=False, error=str(e))

    async def refund_payment(
        self, provider_ref: str, amount: float
    ) -> RefundResult:
        try:
            client = self._get_client()
            payments = client.order.payments(provider_ref)
            payment_id = payments["items"][0]["id"] if payments["items"] else None
            if not payment_id:
                return RefundResult(success=False, error="No payment found for order")
            refund = client.payment.refund(payment_id, int(amount * 100))
            return RefundResult(success=True, refund_ref=refund["id"])
        except Exception as e:
            logger.error("Razorpay refund failed: %s", e)
            return RefundResult(success=False, error=str(e))

    async def verify_keys(self, config: dict) -> bool:
        try:
            import razorpay
            client = razorpay.Client(
                auth=(config.get("razorpay_key_id", ""), config.get("razorpay_key_secret", ""))
            )
            client.order.all({"count": 1})
            return True
        except Exception:
            return False
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/payments/providers/
git commit -m "feat(payments): scaffold Stripe and Razorpay providers"
```

---

## Task 8: Payout Model + Service + Router

**Files:**
- Create: `backend/app/core/payouts/__init__.py`
- Create: `backend/app/core/payouts/models.py`
- Create: `backend/app/core/payouts/schemas.py`
- Create: `backend/app/core/payouts/service.py`
- Create: `backend/app/core/payouts/router.py`
- Create: `backend/tests/test_payout_unit.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create payout directories**

```bash
mkdir -p backend/app/core/payouts
touch backend/app/core/payouts/__init__.py
```

- [ ] **Step 2: Write payout unit tests**

Create `backend/tests/test_payout_unit.py`:

```python
import uuid
from datetime import UTC, datetime

from app.core.payouts.models import Payout, PayoutItem, TENANT_PAYOUT_TABLES


def test_payout_model_defaults():
    p = Payout(
        owner_id=uuid.uuid4(),
        amount=5000.0,
        currency="INR",
    )
    assert p.status == "pending"
    assert p.settled_at is None
    assert p.settled_by is None


def test_payout_item_model():
    item = PayoutItem(
        payout_id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        booking_total=1000.0,
        commission=50.0,
        owner_amount=950.0,
    )
    assert item.booking_total == 1000.0
    assert item.owner_amount == 950.0


def test_tenant_payout_tables():
    assert "payouts" in TENANT_PAYOUT_TABLES
    assert "payout_items" in TENANT_PAYOUT_TABLES
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_payout_unit.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Create payout models**

Create `backend/app/core/payouts/models.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel

TENANT_PAYOUT_TABLES: set[str] = {"payouts", "payout_items"}


class Payout(SQLModel, table=True):
    __tablename__ = "payouts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    amount: float = Field(default=0.0)
    currency: str = Field(default="USD", max_length=10)
    status: str = Field(default="pending", max_length=20)
    period_start: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    period_end: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    settled_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    settled_by: uuid.UUID | None = Field(default=None)
    provider_ref: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class PayoutItem(SQLModel, table=True):
    __tablename__ = "payout_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    payout_id: uuid.UUID = Field(foreign_key="payouts.id", index=True)
    booking_id: uuid.UUID = Field(foreign_key="bookings.id", index=True)
    booking_total: float = Field(default=0.0)
    commission: float = Field(default=0.0)
    owner_amount: float = Field(default=0.0)
```

- [ ] **Step 5: Create payout schemas**

Create `backend/app/core/payouts/schemas.py`:

```python
import uuid
from datetime import datetime

from pydantic import BaseModel


class PayoutCreate(BaseModel):
    owner_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    notes: str | None = None


class PayoutItemResponse(BaseModel):
    id: uuid.UUID
    payout_id: uuid.UUID
    booking_id: uuid.UUID
    booking_total: float
    commission: float
    owner_amount: float

    model_config = {"from_attributes": True}


class PayoutResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    amount: float
    currency: str
    status: str
    period_start: datetime | None
    period_end: datetime | None
    settled_at: datetime | None
    settled_by: uuid.UUID | None
    provider_ref: str | None
    notes: str | None
    created_at: datetime
    items: list[PayoutItemResponse] = []

    model_config = {"from_attributes": True}


class OwnerBalance(BaseModel):
    owner_id: uuid.UUID
    owner_name: str
    owner_email: str
    pending_amount: float
    currency: str
    booking_count: int
    last_settled: datetime | None
```

- [ ] **Step 6: Create payout service**

Create `backend/app/core/payouts/service.py`:

```python
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlmodel import select, func, and_
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
) -> list[Booking]:
    settled_booking_ids_subq = select(PayoutItem.booking_id)

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

    stmt = stmt.order_by(Booking.end_time.asc())
    result = await session.exec(stmt)
    return list(result.all())


async def create_payout(
    session: AsyncSession,
    owner_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
    admin_id: uuid.UUID,
    notes: str | None = None,
) -> Payout:
    bookings = await get_unsettled_bookings(
        session, owner_id, period_start, period_end
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
```

- [ ] **Step 7: Create payout router**

Create `backend/app/core/payouts/router.py`:

```python
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import require_permission
from app.core.auth.models import User
from app.core.payouts.schemas import (
    OwnerBalance,
    PayoutCreate,
    PayoutItemResponse,
    PayoutResponse,
)
from app.core.payouts.service import (
    create_payout,
    get_owner_balances,
    get_payout,
    get_payout_items,
    get_unsettled_bookings,
    list_payouts,
    settle_payout,
)
from app.database import get_db
from app.domains.bookings.schemas import BookingResponse

router = APIRouter(prefix="/api/payouts", tags=["payouts"])


def _require_admin():
    return require_permission("*:*:*")


@router.get("/balances", response_model=list[OwnerBalance])
async def owner_balances(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    return await get_owner_balances(session)


@router.get("/owner/{owner_id}/bookings", response_model=list[BookingResponse])
async def unsettled_bookings(
    owner_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    return await get_unsettled_bookings(session, owner_id)


@router.post("", response_model=PayoutResponse, status_code=201)
async def create_new_payout(
    data: PayoutCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    payout = await create_payout(
        session, data.owner_id, data.period_start, data.period_end,
        admin_id=user.id, notes=data.notes,
    )
    items = await get_payout_items(session, payout.id)
    resp = PayoutResponse.model_validate(payout)
    resp.items = [PayoutItemResponse.model_validate(i) for i in items]
    return resp


@router.post("/{payout_id}/settle", response_model=PayoutResponse)
async def settle(
    payout_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    return await settle_payout(session, payout_id, user.id)


@router.get("", response_model=list[PayoutResponse])
async def list_all_payouts(
    owner_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    return await list_payouts(session, owner_id, status, offset, limit)


@router.get("/{payout_id}", response_model=PayoutResponse)
async def get_one_payout(
    payout_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    payout = await get_payout(session, payout_id)
    items = await get_payout_items(session, payout_id)
    resp = PayoutResponse.model_validate(payout)
    resp.items = [PayoutItemResponse.model_validate(i) for i in items]
    return resp
```

- [ ] **Step 8: Register payout router in main.py**

In `backend/app/main.py`, add import:

```python
from app.core.payouts.router import router as payout_router
```

Add after `app.include_router(payment_router)`:

```python
app.include_router(payout_router)
```

- [ ] **Step 9: Run tests**

Run: `cd backend && python -m pytest tests/test_payout_unit.py -v`
Expected: All 3 tests PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/core/payouts/ backend/tests/test_payout_unit.py backend/app/main.py
git commit -m "feat(payouts): add payout model, service, and router"
```

---

## Task 9: Staff Disable Cascade + Activate + Public Filter

**Files:**
- Modify: `backend/app/core/admin/service.py:187-197`
- Modify: `backend/app/core/admin/router.py`
- Modify: `backend/app/core/admin/schemas.py`
- Modify: `backend/app/domains/resources/service.py:170-187`

- [ ] **Step 1: Add DeactivationImpactResponse to admin schemas**

In `backend/app/core/admin/schemas.py`, add at the end:

```python
class DeactivationImpactResponse(BaseModel):
    resources_count: int
    pending_bookings_count: int
```

- [ ] **Step 2: Update deactivate_user with cascade logic**

Replace `deactivate_user` in `backend/app/core/admin/service.py` (lines 187-197):

```python
async def deactivate_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    user.updated_at = datetime.now(UTC)
    session.add(user)

    from app.domains.resources.models import Resource
    from app.domains.bookings.models import Booking

    resource_result = await session.exec(
        select(Resource).where(
            Resource.owner_id == user_id, Resource.status == "active"
        )
    )
    resources = list(resource_result.all())
    resource_ids = []
    for r in resources:
        r.status = "suspended"
        r.suspension_reason = "owner_deactivated"
        session.add(r)
        resource_ids.append(r.id)

    if resource_ids:
        booking_result = await session.exec(
            select(Booking).where(
                Booking.resource_id.in_(resource_ids),
                Booking.status == "pending",
            )
        )
        for booking in booking_result.all():
            booking.status = "rejected"
            booking.cancellation_reason = "Resource owner deactivated"
            booking.updated_at = datetime.now(UTC)
            booking.version += 1
            session.add(booking)

    await session.commit()
    await session.refresh(user)
    return user
```

- [ ] **Step 3: Add activate_user function to admin service**

Add at the end of `backend/app/core/admin/service.py`:

```python
async def activate_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    result = await session.exec(select(User).where(User.id == user_id))
    user = result.first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    user.updated_at = datetime.now(UTC)
    session.add(user)

    from app.domains.resources.models import Resource

    resource_result = await session.exec(
        select(Resource).where(
            Resource.owner_id == user_id,
            Resource.suspension_reason == "owner_deactivated",
        )
    )
    for r in resource_result.all():
        r.status = "active"
        r.suspension_reason = None
        session.add(r)

    await session.commit()
    await session.refresh(user)
    return user


async def get_deactivation_impact(
    session: AsyncSession, user_id: uuid.UUID
) -> dict:
    from app.domains.resources.models import Resource
    from app.domains.bookings.models import Booking

    resource_result = await session.exec(
        select(Resource).where(
            Resource.owner_id == user_id, Resource.status == "active"
        )
    )
    resources = list(resource_result.all())
    resource_ids = [r.id for r in resources]

    pending_count = 0
    if resource_ids:
        from sqlmodel import func
        count_result = await session.exec(
            select(func.count(Booking.id)).where(
                Booking.resource_id.in_(resource_ids),
                Booking.status == "pending",
            )
        )
        pending_count = count_result.one()

    return {
        "resources_count": len(resources),
        "pending_bookings_count": pending_count,
    }
```

- [ ] **Step 4: Add activate and impact-check endpoints to admin router**

In `backend/app/core/admin/router.py`, update the imports to include new functions and schema:

```python
from app.core.admin.service import (
    activate_user,
    add_domain,
    deactivate_user,
    get_deactivation_impact,
    get_theme,
    invite_staff,
    list_domains,
    list_staff,
    remove_domain,
    update_tenant_config,
    update_theme,
)
```

Add `DeactivationImpactResponse` to the schemas import:

```python
from app.core.admin.schemas import (
    DeactivationImpactResponse,
    DomainCreate,
    DomainResponse,
    StaffInvite,
    StaffUserResponse,
    TenantConfigUpdate,
    TenantResponse,
    ThemeResponse,
    ThemeUpdate,
)
```

Add these endpoints after the deactivate endpoint (line 146):

```python
@router.post("/staff/{user_id}/activate", response_model=StaffUserResponse)
async def activate_staff(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(_require_admin()),
):
    activated = await activate_user(session, user_id)
    return StaffUserResponse.model_validate(activated)


@router.get("/staff/{user_id}/deactivation-impact", response_model=DeactivationImpactResponse)
async def staff_deactivation_impact(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_admin()),
):
    impact = await get_deactivation_impact(session, user_id)
    return DeactivationImpactResponse(**impact)
```

- [ ] **Step 5: Default status=active for public resource listing**

In `backend/app/domains/resources/service.py`, update `list_resources` (line 170-187). Change the status filter logic:

Replace:
```python
    if status_filter:
        stmt = stmt.where(Resource.status == status_filter)
```

With:
```python
    if status_filter:
        stmt = stmt.where(Resource.status == status_filter)
    else:
        stmt = stmt.where(Resource.status == "active")
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/admin/ backend/app/domains/resources/service.py
git commit -m "feat(admin): add staff disable cascade, activate endpoint, and default active filter"
```

---

## Task 10: Frontend Types for Commission, Payment, Payout

**Files:**
- Create: `frontend/src/types/commission.ts`
- Create: `frontend/src/types/payment.ts`
- Create: `frontend/src/types/payout.ts`
- Modify: `frontend/src/types/api.ts`

- [ ] **Step 1: Create commission types**

Create `frontend/src/types/commission.ts`:

```typescript
export interface CommissionConfig {
  owner_percent: number;
  owner_fixed: number;
  customer_percent: number;
  customer_fixed: number;
  currency: string;
}

export interface CommissionConfigResponse {
  entity_type: string;
  entity_id: string;
  config: CommissionConfig | null;
  inherited_from: string | null;
}

export interface CommissionConfigUpdate {
  owner_percent?: number;
  owner_fixed?: number;
  customer_percent?: number;
  customer_fixed?: number;
  currency?: string;
}

export interface CommissionPreview {
  amount: number;
  currency: string;
  config: CommissionConfig | null;
  service_fee: number;
  platform_commission: number;
  owner_payout: number;
  customer_total: number;
}
```

- [ ] **Step 2: Create payment types**

Create `frontend/src/types/payment.ts`:

```typescript
export interface PaymentResponse {
  id: string;
  booking_id: string;
  amount: number;
  currency: string;
  provider: string;
  status: string;
  provider_ref: string | null;
  paid_at: string | null;
  refund_amount: number | null;
  refunded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MarkPaidRequest {
  notes?: string;
}

export interface RefundRequest {
  amount?: number;
  reason?: string;
}
```

- [ ] **Step 3: Create payout types**

Create `frontend/src/types/payout.ts`:

```typescript
export interface PayoutItemResponse {
  id: string;
  payout_id: string;
  booking_id: string;
  booking_total: number;
  commission: number;
  owner_amount: number;
}

export interface PayoutResponse {
  id: string;
  owner_id: string;
  amount: number;
  currency: string;
  status: string;
  period_start: string | null;
  period_end: string | null;
  settled_at: string | null;
  settled_by: string | null;
  provider_ref: string | null;
  notes: string | null;
  created_at: string;
  items: PayoutItemResponse[];
}

export interface PayoutCreate {
  owner_id: string;
  period_start: string;
  period_end: string;
  notes?: string;
}

export interface OwnerBalance {
  owner_id: string;
  owner_name: string;
  owner_email: string;
  pending_amount: number;
  currency: string;
  booking_count: number;
  last_settled: string | null;
}

export interface DeactivationImpact {
  resources_count: number;
  pending_bookings_count: number;
}
```

- [ ] **Step 4: Update BookingResponse in api.ts**

In `frontend/src/types/api.ts`, add commission fields to `BookingResponse` after `currency`:

```typescript
  service_fee: number;
  platform_commission: number;
  owner_payout: number;
  customer_total: number;
```

Add `user_id` to `BookingCreate`:

```typescript
export interface BookingCreate {
  resource_id: string;
  hold_token: string;
  start_time: string;
  end_time: string;
  notes?: string;
  auto_confirm?: boolean;
  user_id?: string;
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/commission.ts frontend/src/types/payment.ts frontend/src/types/payout.ts frontend/src/types/api.ts
git commit -m "feat(frontend): add commission, payment, and payout TypeScript types"
```

---

## Task 11: Commission Settings Admin Page

**Files:**
- Create: `frontend/src/app/admin/settings/commission/page.tsx`
- Modify: `frontend/src/components/shell/sub-nav.tsx`

- [ ] **Step 1: Add commission and payments sub-nav items**

In `frontend/src/components/shell/sub-nav.tsx`, update the `/admin/settings` section in `STATIC_NAV_CONFIG`:

```typescript
  "/admin/settings": {
    title: "Settings",
    items: [
      { href: "/admin/settings#general", label: "General" },
      { href: "/admin/settings#domains", label: "Domains" },
      { href: "/admin/settings/commission", label: "Commission" },
      { href: "/admin/settings/payments", label: "Payments" },
    ],
  },
```

- [ ] **Step 2: Create commission settings page**

Create `frontend/src/app/admin/settings/commission/page.tsx`:

```typescript
"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Pencil } from "lucide-react";
import api from "@/lib/api";
import type { ResourceTypeResponse } from "@/types/api";
import type {
  CommissionConfig,
  CommissionConfigResponse,
  CommissionPreview,
} from "@/types/commission";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "sonner";

export default function CommissionSettingsPage() {
  const queryClient = useQueryClient();
  const [editingType, setEditingType] = useState<ResourceTypeResponse | null>(null);

  const { data: resourceTypes, isLoading } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
  });

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Commission Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure platform commission per resource type. Per-resource overrides can be set in the resource edit form.
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}

      <div className="grid gap-4">
        {resourceTypes?.map((rt) => (
          <CommissionTypeCard
            key={rt.id}
            resourceType={rt}
            onEdit={() => setEditingType(rt)}
          />
        ))}
      </div>

      {editingType && (
        <CommissionEditSheet
          resourceType={editingType}
          open={!!editingType}
          onClose={() => {
            setEditingType(null);
            queryClient.invalidateQueries({ queryKey: ["commission"] });
          }}
        />
      )}
    </div>
  );
}

function CommissionTypeCard({
  resourceType,
  onEdit,
}: {
  resourceType: ResourceTypeResponse;
  onEdit: () => void;
}) {
  const { data: commission } = useQuery({
    queryKey: ["commission", "resource-type", resourceType.id],
    queryFn: async () => {
      const { data } = await api.get<CommissionConfigResponse>(
        `/commission/resource-type/${resourceType.id}`
      );
      return data;
    },
  });

  const config = commission?.config;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle className="text-base">{resourceType.name}</CardTitle>
          <CardDescription>
            {config
              ? `Owner: ${config.owner_percent}% + ${config.currency} ${config.owner_fixed} | Customer: ${config.customer_percent}% + ${config.currency} ${config.customer_fixed}`
              : "No commission configured"}
          </CardDescription>
        </div>
        <Button size="sm" variant="outline" onClick={onEdit}>
          <Pencil className="mr-1 h-3 w-3" />
          Edit
        </Button>
      </CardHeader>
    </Card>
  );
}

function CommissionEditSheet({
  resourceType,
  open,
  onClose,
}: {
  resourceType: ResourceTypeResponse;
  open: boolean;
  onClose: () => void;
}) {
  const [ownerPercent, setOwnerPercent] = useState(0);
  const [ownerFixed, setOwnerFixed] = useState(0);
  const [customerPercent, setCustomerPercent] = useState(0);
  const [customerFixed, setCustomerFixed] = useState(0);
  const [loaded, setLoaded] = useState(false);

  const { data: commission } = useQuery({
    queryKey: ["commission", "resource-type", resourceType.id],
    queryFn: async () => {
      const { data } = await api.get<CommissionConfigResponse>(
        `/commission/resource-type/${resourceType.id}`
      );
      return data;
    },
  });

  if (commission && !loaded) {
    const c = commission.config;
    if (c) {
      setOwnerPercent(c.owner_percent);
      setOwnerFixed(c.owner_fixed);
      setCustomerPercent(c.customer_percent);
      setCustomerFixed(c.customer_fixed);
    }
    setLoaded(true);
  }

  const { data: preview } = useQuery({
    queryKey: [
      "commission-preview",
      resourceType.id,
      ownerPercent,
      ownerFixed,
      customerPercent,
      customerFixed,
    ],
    queryFn: async () => {
      const { data } = await api.get<CommissionPreview>(
        `/commission/preview?resource_id=${resourceType.id}&amount=1000`
      );
      return data;
    },
    enabled: false,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      await api.patch(`/commission/resource-type/${resourceType.id}`, {
        owner_percent: ownerPercent,
        owner_fixed: ownerFixed,
        customer_percent: customerPercent,
        customer_fixed: customerFixed,
      });
    },
    onSuccess: () => {
      toast.success("Commission updated");
      onClose();
    },
    onError: () => {
      toast.error("Failed to update commission");
    },
  });

  const sampleTotal = 1000;
  const ownerComm = Math.round((sampleTotal * ownerPercent) / 100 + ownerFixed);
  const serviceFee = Math.round((sampleTotal * customerPercent) / 100 + customerFixed);

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="overflow-y-auto sm:max-w-md">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>Edit Commission — {resourceType.name}</SheetTitle>
          <SheetDescription>
            Set platform commission for all {resourceType.name.toLowerCase()} resources
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-5 px-6 pb-6">
          <div className="space-y-4 rounded-lg border p-4">
            <p className="text-sm font-medium">Owner Deduction</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Percentage (%)</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={ownerPercent}
                  onChange={(e) => setOwnerPercent(parseFloat(e.target.value) || 0)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Fixed Amount</Label>
                <Input
                  type="number"
                  step="1"
                  min="0"
                  value={ownerFixed}
                  onChange={(e) => setOwnerFixed(parseFloat(e.target.value) || 0)}
                />
              </div>
            </div>
          </div>

          <div className="space-y-4 rounded-lg border p-4">
            <p className="text-sm font-medium">Customer Service Fee</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Percentage (%)</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={customerPercent}
                  onChange={(e) => setCustomerPercent(parseFloat(e.target.value) || 0)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Fixed Amount</Label>
                <Input
                  type="number"
                  step="1"
                  min="0"
                  value={customerFixed}
                  onChange={(e) => setCustomerFixed(parseFloat(e.target.value) || 0)}
                />
              </div>
            </div>
          </div>

          <div className="rounded-lg bg-muted/50 p-4 text-sm space-y-2">
            <p className="font-medium">Preview (on a {sampleTotal} booking)</p>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Owner gets</span>
              <span className="font-medium">{sampleTotal - ownerComm}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Customer pays</span>
              <span className="font-medium">{sampleTotal + serviceFee}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Platform earns</span>
              <span className="font-medium text-primary">{ownerComm + serviceFee}</span>
            </div>
          </div>

          <div className="flex gap-3 border-t pt-5">
            <Button
              className="flex-1"
              onClick={() => saveMutation.mutate()}
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              Save
            </Button>
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/admin/settings/commission/ frontend/src/components/shell/sub-nav.tsx
git commit -m "feat(frontend): add commission settings admin page"
```

---

## Task 12: Payment Gateway Settings Admin Page

**Files:**
- Create: `frontend/src/app/admin/settings/payments/page.tsx`

- [ ] **Step 1: Create payment gateway settings page**

Create `frontend/src/app/admin/settings/payments/page.tsx`:

```typescript
"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, Loader2, CheckCircle, XCircle } from "lucide-react";
import api from "@/lib/api";
import type { TenantResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

type Provider = "manual" | "stripe" | "razorpay";

function maskKey(key: string): string {
  if (!key || key.length < 8) return "••••••••";
  return "••••••••" + key.slice(-4);
}

export default function PaymentSettingsPage() {
  const queryClient = useQueryClient();

  const { data: tenant } = useQuery({
    queryKey: ["admin-tenant"],
    queryFn: async () => {
      const { data } = await api.get<TenantResponse>("/admin/tenant");
      return data;
    },
  });

  const config = tenant?.config || {};
  const currentProvider = (config.payment_provider as Provider) || "manual";

  const [provider, setProvider] = useState<Provider>(currentProvider);
  const [stripeSecret, setStripeSecret] = useState("");
  const [stripePub, setStripePub] = useState("");
  const [razorpayId, setRazorpayId] = useState("");
  const [razorpaySecret, setRazorpaySecret] = useState("");
  const [showKeys, setShowKeys] = useState(false);

  useEffect(() => {
    if (tenant) {
      const c = tenant.config || {};
      setProvider((c.payment_provider as Provider) || "manual");
    }
  }, [tenant]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const updatedConfig: Record<string, unknown> = {
        ...config,
        payment_provider: provider,
      };
      if (stripeSecret) updatedConfig.stripe_secret_key = stripeSecret;
      if (stripePub) updatedConfig.stripe_publishable_key = stripePub;
      if (razorpayId) updatedConfig.razorpay_key_id = razorpayId;
      if (razorpaySecret) updatedConfig.razorpay_key_secret = razorpaySecret;

      await api.patch("/admin/tenant", { config: updatedConfig });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tenant"] });
      toast.success("Payment settings saved");
      setStripeSecret("");
      setStripePub("");
      setRazorpayId("");
      setRazorpaySecret("");
    },
    onError: () => {
      toast.error("Failed to save settings");
    },
  });

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Payment Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Configure payment gateway. Manual mode requires admin to mark payments as paid.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Active Provider</CardTitle>
          <CardDescription>Select which payment provider to use</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={provider} onValueChange={(v) => setProvider(v as Provider)}>
            <SelectTrigger className="w-[250px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="manual">Manual (Admin marks paid)</SelectItem>
              <SelectItem value="stripe">Stripe</SelectItem>
              <SelectItem value="razorpay">Razorpay</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {provider === "stripe" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Stripe Configuration</CardTitle>
              <CardDescription>Enter your Stripe API keys</CardDescription>
            </div>
            {config.stripe_secret_key && (
              <Badge variant="success">Configured</Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Secret Key</Label>
              <div className="flex gap-2">
                <Input
                  type={showKeys ? "text" : "password"}
                  placeholder={config.stripe_secret_key ? maskKey(config.stripe_secret_key as string) : "sk_..."}
                  value={stripeSecret}
                  onChange={(e) => setStripeSecret(e.target.value)}
                />
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setShowKeys(!showKeys)}
                >
                  {showKeys ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Publishable Key</Label>
              <Input
                type={showKeys ? "text" : "password"}
                placeholder={config.stripe_publishable_key ? maskKey(config.stripe_publishable_key as string) : "pk_..."}
                value={stripePub}
                onChange={(e) => setStripePub(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {provider === "razorpay" && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Razorpay Configuration</CardTitle>
              <CardDescription>Enter your Razorpay API keys</CardDescription>
            </div>
            {config.razorpay_key_id && (
              <Badge variant="success">Configured</Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Key ID</Label>
              <Input
                type={showKeys ? "text" : "password"}
                placeholder={config.razorpay_key_id ? maskKey(config.razorpay_key_id as string) : "rzp_..."}
                value={razorpayId}
                onChange={(e) => setRazorpayId(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Key Secret</Label>
              <div className="flex gap-2">
                <Input
                  type={showKeys ? "text" : "password"}
                  placeholder={config.razorpay_key_secret ? maskKey(config.razorpay_key_secret as string) : "secret..."}
                  value={razorpaySecret}
                  onChange={(e) => setRazorpaySecret(e.target.value)}
                />
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => setShowKeys(!showKeys)}
                >
                  {showKeys ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex gap-3">
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={saveMutation.isPending}
        >
          {saveMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
          Save Settings
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/admin/settings/payments/
git commit -m "feat(frontend): add payment gateway settings admin page"
```

---

## Task 13: Payouts Admin Page

**Files:**
- Create: `frontend/src/app/admin/payouts/page.tsx`
- Modify: `frontend/src/components/shell/icon-rail.tsx`
- Modify: `frontend/src/components/shell/sub-nav.tsx`

- [ ] **Step 1: Add Payouts to icon rail**

In `frontend/src/components/shell/icon-rail.tsx`, add `Banknote` to the lucide imports:

```typescript
import {
  Banknote,
  Bell,
  Box,
  CalendarDays,
  LayoutDashboard,
  Palette,
  Settings,
  Star,
  Users,
  Sun,
  Moon,
  LogOut,
} from "lucide-react";
```

Add the payouts nav item to `NAV_ITEMS` after the bookings item:

```typescript
  { href: "/admin/bookings", icon: CalendarDays, label: "Bookings" },
  { href: "/admin/payouts", icon: Banknote, label: "Payouts" },
```

- [ ] **Step 2: Add payouts sub-nav**

In `frontend/src/components/shell/sub-nav.tsx`, add to `STATIC_NAV_CONFIG`:

```typescript
  "/admin/payouts": {
    title: "Payouts",
    items: [
      { href: "/admin/payouts", label: "Balances" },
      { href: "/admin/payouts?tab=history", label: "History" },
    ],
  },
```

- [ ] **Step 3: Create payouts page**

Create `frontend/src/app/admin/payouts/page.tsx`:

```typescript
"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, CheckCircle } from "lucide-react";
import api from "@/lib/api";
import type { OwnerBalance, PayoutCreate, PayoutResponse } from "@/types/payout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { toast } from "sonner";

export default function PayoutsPage() {
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") || "balances";

  return (
    <div className="flex-1 space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Payouts</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage resource owner payouts and settlements
        </p>
      </div>

      {tab === "balances" && <BalancesTab />}
      {tab === "history" && <HistoryTab />}
    </div>
  );
}

function BalancesTab() {
  const queryClient = useQueryClient();
  const [selectedOwner, setSelectedOwner] = useState<OwnerBalance | null>(null);

  const { data: balances, isLoading } = useQuery({
    queryKey: ["payout-balances"],
    queryFn: async () => {
      const { data } = await api.get<OwnerBalance[]>("/payouts/balances");
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!balances || balances.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No pending payouts
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="grid gap-4">
        {balances.map((b) => (
          <Card key={b.owner_id}>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base">{b.owner_name}</CardTitle>
                <CardDescription>{b.owner_email}</CardDescription>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold">
                  {b.currency} {b.pending_amount.toFixed(2)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {b.booking_count} booking{b.booking_count !== 1 ? "s" : ""}
                </p>
              </div>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <span className="text-xs text-muted-foreground">
                {b.last_settled
                  ? `Last settled: ${new Date(b.last_settled).toLocaleDateString()}`
                  : "Never settled"}
              </span>
              <Button size="sm" onClick={() => setSelectedOwner(b)}>
                Create Payout
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {selectedOwner && (
        <CreatePayoutSheet
          owner={selectedOwner}
          open={!!selectedOwner}
          onClose={() => {
            setSelectedOwner(null);
            queryClient.invalidateQueries({ queryKey: ["payout-balances"] });
          }}
        />
      )}
    </>
  );
}

function CreatePayoutSheet({
  owner,
  open,
  onClose,
}: {
  owner: OwnerBalance;
  open: boolean;
  onClose: () => void;
}) {
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload: PayoutCreate = {
        owner_id: owner.owner_id,
        period_start: new Date(periodStart).toISOString(),
        period_end: new Date(periodEnd + "T23:59:59").toISOString(),
        notes: notes || undefined,
      };
      const { data } = await api.post<PayoutResponse>("/payouts", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Payout created");
      onClose();
    },
    onError: () => {
      toast.error("Failed to create payout");
    },
  });

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="sm:max-w-md">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>Create Payout — {owner.owner_name}</SheetTitle>
          <SheetDescription>
            Pending: {owner.currency} {owner.pending_amount.toFixed(2)} from {owner.booking_count} bookings
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-4 px-6 pb-6">
          <div className="space-y-2">
            <Label>Period Start</Label>
            <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Period End</Label>
            <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Notes (optional)</Label>
            <Input
              placeholder="Settlement notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <div className="flex gap-3 border-t pt-4">
            <Button
              className="flex-1"
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !periodStart}
            >
              {createMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
              Create Payout
            </Button>
            <Button variant="outline" onClick={onClose}>Cancel</Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function HistoryTab() {
  const queryClient = useQueryClient();

  const { data: payouts, isLoading } = useQuery({
    queryKey: ["payouts"],
    queryFn: async () => {
      const { data } = await api.get<PayoutResponse[]>("/payouts");
      return data;
    },
  });

  const settleMutation = useMutation({
    mutationFn: async (payoutId: string) => {
      const { data } = await api.post<PayoutResponse>(`/payouts/${payoutId}/settle`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payouts"] });
      queryClient.invalidateQueries({ queryKey: ["payout-balances"] });
      toast.success("Payout settled");
    },
    onError: () => {
      toast.error("Failed to settle payout");
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!payouts || payouts.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground">
          No payouts yet
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {payouts.map((p) => (
        <Card key={p.id}>
          <CardContent className="flex items-center justify-between py-4">
            <div>
              <p className="font-medium">
                {p.currency} {p.amount.toFixed(2)}
              </p>
              <p className="text-xs text-muted-foreground">
                {p.period_start
                  ? `${new Date(p.period_start).toLocaleDateString()} — ${new Date(p.period_end!).toLocaleDateString()}`
                  : "No period"}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={p.status === "settled" ? "success" : "secondary"}>
                {p.status}
              </Badge>
              {p.status === "pending" && (
                <Button
                  size="sm"
                  onClick={() => settleMutation.mutate(p.id)}
                  disabled={settleMutation.isPending}
                >
                  {settleMutation.isPending ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <CheckCircle className="mr-1 h-3 w-3" />
                  )}
                  Settle
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/admin/payouts/ frontend/src/components/shell/icon-rail.tsx frontend/src/components/shell/sub-nav.tsx
git commit -m "feat(frontend): add payouts admin page with balances and history tabs"
```

---

## Task 14: Add "Mark Paid" to Booking Actions + Payment Info in Detail

**Files:**
- Modify: `frontend/src/components/bookings/booking-actions.tsx`
- Modify: `frontend/src/app/admin/bookings/[id]/page.tsx`

- [ ] **Step 1: Read current booking-actions.tsx**

Read the file to understand current action patterns before modifying.

- [ ] **Step 2: Add Mark Paid action to booking actions**

In `frontend/src/components/bookings/booking-actions.tsx`, add a "Mark Paid" button that:
- Queries `GET /api/payments/booking/{booking_id}` to check payment status
- If no payment exists, shows "Create Payment" button that calls `POST /api/payments/booking/{booking_id}`
- If payment exists and status is "pending", shows "Mark Paid" button that calls `POST /api/payments/{payment_id}/mark-paid`
- If payment is "paid", shows a green "Paid" badge

Add these imports:

```typescript
import type { PaymentResponse } from "@/types/payment";
```

Add a `PaymentAction` component:

```typescript
function PaymentAction({ bookingId }: { bookingId: string }) {
  const queryClient = useQueryClient();

  const { data: payment } = useQuery({
    queryKey: ["payment", bookingId],
    queryFn: async () => {
      try {
        const { data } = await api.get<PaymentResponse>(`/payments/booking/${bookingId}`);
        return data;
      } catch {
        return null;
      }
    },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<PaymentResponse>(`/payments/booking/${bookingId}`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payment", bookingId] });
      toast.success("Payment created");
    },
    onError: () => toast.error("Failed to create payment"),
  });

  const markPaidMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<PaymentResponse>(`/payments/${payment!.id}/mark-paid`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["payment", bookingId] });
      toast.success("Payment marked as paid");
    },
    onError: () => toast.error("Failed to mark paid"),
  });

  if (!payment) {
    return (
      <Button size="sm" variant="outline" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
        {createMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
        Create Payment
      </Button>
    );
  }

  if (payment.status === "paid") {
    return <Badge variant="success">Paid</Badge>;
  }

  if (payment.status === "pending") {
    return (
      <Button size="sm" onClick={() => markPaidMutation.mutate()} disabled={markPaidMutation.isPending}>
        {markPaidMutation.isPending && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
        Mark Paid
      </Button>
    );
  }

  return <Badge variant="secondary">{payment.status}</Badge>;
}
```

Render `<PaymentAction bookingId={booking.id} />` in the actions area of each booking.

- [ ] **Step 3: Add commission breakdown to booking detail page**

In `frontend/src/app/admin/bookings/[id]/page.tsx`, add a commission breakdown card after the booking details. Display:
- Total Price, Service Fee, Customer Total
- Platform Commission, Owner Payout

```typescript
<Card>
  <CardHeader>
    <CardTitle className="text-base">Financial Breakdown</CardTitle>
  </CardHeader>
  <CardContent className="space-y-2 text-sm">
    <div className="flex justify-between">
      <span className="text-muted-foreground">Base Price</span>
      <span>{booking.currency} {booking.total_price.toFixed(2)}</span>
    </div>
    <div className="flex justify-between">
      <span className="text-muted-foreground">Service Fee</span>
      <span>{booking.currency} {booking.service_fee.toFixed(2)}</span>
    </div>
    <div className="flex justify-between border-t pt-2 font-medium">
      <span>Customer Total</span>
      <span>{booking.currency} {booking.customer_total.toFixed(2)}</span>
    </div>
    <div className="flex justify-between text-muted-foreground">
      <span>Platform Commission</span>
      <span>{booking.currency} {booking.platform_commission.toFixed(2)}</span>
    </div>
    <div className="flex justify-between font-medium">
      <span>Owner Payout</span>
      <span>{booking.currency} {booking.owner_payout.toFixed(2)}</span>
    </div>
  </CardContent>
</Card>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/bookings/booking-actions.tsx frontend/src/app/admin/bookings/\[id\]/page.tsx
git commit -m "feat(frontend): add mark-paid action and commission breakdown to booking detail"
```

---

## Self-Review

### Spec Coverage Check

| Spec Section | Task |
|-------------|------|
| 1. Commission System (config, calculation, resolution) | Task 1, 2, 3 |
| 1.4 Commission Admin UI | Task 11 |
| 1.5 Commission Endpoints | Task 3 |
| 2. Payment System (provider, model, flow) | Task 5, 6 |
| 2.4 Payment Endpoints | Task 6 |
| 3. Payout & Settlement | Task 8 |
| 3.4 Payout Admin UI | Task 13 |
| 4. Admin Gateway Settings | Task 12 |
| 5. Admin Booking on Behalf | Task 4 (integrated with commission) |
| 6. Staff Disable Cascade | Task 9 |
| 6.3 Public Query Filter | Task 9 |
| 7. Key Files | All tasks cover listed files |
| 8. Implementation Order | Tasks ordered 1-14 match spec order |

### Placeholder Scan
No TBD, TODO, "implement later", "similar to Task N", or vague steps found.

### Type Consistency
- `CommissionConfig` used consistently across schemas.py, service.py, router.py, and frontend types
- `PaymentResult`/`RefundResult` used consistently across provider.py and all provider implementations
- `calculate_breakdown` returns `dict` with keys `service_fee`, `platform_commission`, `owner_payout`, `customer_total` — matches Booking model fields
- `BookingCreate.user_id` is `uuid.UUID | None` in backend, `string | undefined` in frontend — correct mapping
- `PayoutItem` fields match between model, schema, and frontend type
