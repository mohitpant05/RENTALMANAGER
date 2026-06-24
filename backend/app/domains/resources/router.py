import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user, require_permission
from app.core.auth.models import User
from app.database import get_db
from app.domains.resources.discovery import discover_addons
from app.domains.resources.schemas import (
    AvailabilityCheckRequest,
    AvailabilityCheckResponse,
    AvailabilitySlotResponse,
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
    SchedulesCheckRequest,
    SchedulesCheckResponse,
)
from app.domains.resources.service import (
    check_availability,
    check_schedule_availability,
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
    list_availability_slots,
    list_resource_types,
    list_resources,
    release_resource_hold,
    update_assignment_priority,
    update_resource,
    update_resource_type,
)
from app.domains.resources.templates import RESOURCE_TYPE_TEMPLATES

resource_type_router = APIRouter(prefix="/api/resource-types", tags=["resource-types"])
resource_router = APIRouter(prefix="/api/resources", tags=["resources"])


@resource_type_router.get("", response_model=list[ResourceTypeResponse])
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
    "",
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


@resource_type_router.post("/{resource_type_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_type(
    resource_type_id: uuid.UUID,
    password: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("resources:*:manage")),
):
    from app.core.auth.password import verify_password
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=403, detail="Invalid password")
    await delete_resource_type(session, resource_type_id)


# --- Resource endpoints ---

@resource_router.get("", response_model=list[ResourceResponse])
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


# --- Admin: Availability Slots (must be before /{resource_id} to avoid path conflict) ---

@resource_router.get("/availability/slots", response_model=list[AvailabilitySlotResponse])
async def list_availability_slots_endpoint(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    resource_type_id: uuid.UUID | None = Query(None),
    resource_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("resources:*:manage")),
):
    return await list_availability_slots(
        session, start_date, end_date,
        resource_type_id=resource_type_id,
        resource_id=resource_id,
        status_filter=status,
        search=search,
        offset=offset,
        limit=limit,
    )


@resource_router.get("/{resource_id}", response_model=ResourceResponse)
async def get_one_resource(
    resource_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    return await get_resource(session, resource_id)


@resource_router.post(
    "",
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


@resource_router.post(
    "/{resource_id}/availability/check-schedules",
    response_model=SchedulesCheckResponse,
)
async def check_resource_schedules_availability(
    resource_id: uuid.UUID,
    data: SchedulesCheckRequest,
    session: AsyncSession = Depends(get_db),
):
    available, schedule_states = await check_schedule_availability(
        session, resource_id,
        [s.model_dump() for s in data.schedules],
        data.availability_model,
    )
    return SchedulesCheckResponse(available=available, schedule_states=schedule_states)


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
