import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger("app.resources.service")

from app.core.search.indexing import create_resource_type_index, delete_resource_type_index
from app.core.search.sync import build_document, remove_resource, sync_resource
from app.core.tenancy.context import get_current_tenant
from app.domains.resources.attributes import validate_attributes
from app.domains.resources.availability.strategy import (
    get_availability_provider,
    release_hold,
)
from app.domains.resources.models import Resource, ResourceAssignment, ResourceAvailability, ResourceType
from app.domains.resources.pricing.strategy import get_pricing_provider
from app.domains.resources.schemas import (
    ResourceCreate,
    ResourceTypeCreate,
    ResourceTypeUpdate,
    ResourceUpdate,
)


def _validate_operating_hours(rt: ResourceType, start: datetime, end: datetime) -> None:
    oh = getattr(rt, "operating_hours", None)
    if not oh:
        return
    op_start = oh.get("start")
    op_end = oh.get("end")
    if not op_start or not op_end:
        return
    oh_start_h, oh_start_m = int(op_start[:2]), int(op_start[3:])
    oh_end_h, oh_end_m = int(op_end[:2]), int(op_end[3:])
    booking_start_mins = start.hour * 60 + start.minute
    booking_end_mins = end.hour * 60 + end.minute
    op_start_mins = oh_start_h * 60 + oh_start_m
    op_end_mins = oh_end_h * 60 + oh_end_m
    if booking_start_mins < op_start_mins or booking_end_mins > op_end_mins:
        raise HTTPException(
            status_code=422,
            detail=f"Booking must be within operating hours {op_start}-{op_end}",
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
        hold_config=data.hold_config.model_dump() if data.hold_config else None,
        booking_mode=data.booking_mode,
        operating_hours=data.operating_hours.model_dump() if data.operating_hours else None,
        buffer_minutes=data.buffer_minutes,
    )
    session.add(rt)
    await session.commit()
    await session.refresh(rt)

    tenant_ctx = get_current_tenant()
    if tenant_ctx:
        create_resource_type_index(
            str(tenant_ctx.tenant.id), rt.slug, rt.attribute_schema
        )

    return rt


async def list_resource_types(
    session: AsyncSession, active_only: bool = True
) -> list[ResourceType]:
    stmt = select(ResourceType)
    if active_only:
        stmt = stmt.where(ResourceType.is_active.is_(True))
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
    if "hold_config" in update_data and update_data["hold_config"] is not None:
        from app.domains.resources.schemas import HoldConfig
        update_data["hold_config"] = HoldConfig(**update_data["hold_config"]).model_dump()
    if "operating_hours" in update_data and update_data["operating_hours"] is not None:
        from app.domains.resources.schemas import OperatingHours
        update_data["operating_hours"] = OperatingHours(**update_data["operating_hours"]).model_dump()
    for key, value in update_data.items():
        setattr(rt, key, value)
    rt.updated_at = datetime.now(UTC)
    session.add(rt)
    await session.commit()
    await session.refresh(rt)
    return rt


async def delete_resource_type(
    session: AsyncSession, resource_type_id: uuid.UUID
) -> None:
    rt = await get_resource_type(session, resource_type_id)
    rt.is_active = False
    rt.updated_at = datetime.now(UTC)
    session.add(rt)
    await session.commit()

    tenant_ctx = get_current_tenant()
    if tenant_ctx:
        delete_resource_type_index(str(tenant_ctx.tenant.id), rt.slug)


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

    from app.core.currency.service import to_usd

    tenant_ctx = get_current_tenant()
    tenant_currency = tenant_ctx.tenant.base_currency if tenant_ctx else "USD"
    input_currency = data.currency or tenant_currency
    price_usd = await to_usd(data.base_price, input_currency)

    resource = Resource(
        type_id=data.type_id,
        name=data.name,
        description=data.description,
        location_lat=data.location_lat,
        location_lng=data.location_lng,
        location_address=data.location_address,
        attributes=data.attributes,
        base_price=price_usd,
        currency="USD",
        owner_id=owner_id,
        slot_config=data.slot_config,
    )
    session.add(resource)
    await session.commit()
    await session.refresh(resource)

    if tenant_ctx:
        doc = build_document(
            resource.id, resource.name, resource.description,
            resource.location_lat, resource.location_lng, resource.location_address,
            resource.attributes, resource.base_price, resource.currency,
            resource.status, resource.rating_avg, resource.rating_count,
            rt.slug, resource.created_at,
        )
        sync_resource(str(tenant_ctx.tenant.id), rt.slug, doc)

    return resource


async def list_resources(
    session: AsyncSession,
    type_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    owner_id: uuid.UUID | None = None,
    scope_owner_ids: list[uuid.UUID] | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[Resource]:
    stmt = select(Resource)
    if type_id:
        stmt = stmt.where(Resource.type_id == type_id)
    if status_filter == "all":
        pass
    elif status_filter:
        stmt = stmt.where(Resource.status == status_filter)
    else:
        stmt = stmt.where(Resource.status == "active")
    if owner_id:
        stmt = stmt.where(Resource.owner_id == owner_id)
    if scope_owner_ids is not None:
        stmt = stmt.where(Resource.owner_id.in_(scope_owner_ids))
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
    logger.info("RESOURCE UPDATE STEP 1/7: load resource id=%s", resource_id)
    resource = await get_resource(session, resource_id)
    if resource is None:
        logger.warning("RESOURCE UPDATE STEP 1/7 FAILED — resource %s not found", resource_id)
        raise HTTPException(status_code=404, detail="Resource not found")
    logger.info("RESOURCE UPDATE STEP 1/7 OK — type_id=%s owner_id=%s status=%s",
                 resource.type_id, resource.owner_id, resource.status)

    logger.info("RESOURCE UPDATE STEP 2/7: permission check (is_admin=%s, owner=%s, caller=%s)",
                 is_admin, resource.owner_id, user_id)
    if not is_admin and resource.owner_id != user_id:
        logger.warning("RESOURCE UPDATE STEP 2/7 FAILED — user %s is not admin and not owner",
                        user_id)
        raise HTTPException(status_code=403, detail="Not the resource owner")
    logger.info("RESOURCE UPDATE STEP 2/7 OK")

    if data.attributes is not None:
        logger.info("RESOURCE UPDATE STEP 3/7: validating attributes against schema")
        rt = await get_resource_type(session, resource.type_id)
        if rt.attribute_schema:
            errors = validate_attributes(data.attributes, rt.attribute_schema)
            if errors:
                logger.warning("RESOURCE UPDATE STEP 3/7 FAILED — validation errors: %s", errors)
                raise HTTPException(
                    status_code=422, detail={"attribute_errors": errors}
                )
        logger.info("RESOURCE UPDATE STEP 3/7 OK")
    else:
        logger.info("RESOURCE UPDATE STEP 3/7: no attributes to validate (skipping)")

    logger.info("RESOURCE UPDATE STEP 4/7: build update_data from request")
    update_data = data.model_dump(exclude_unset=True)
    logger.info("RESOURCE UPDATE STEP 4/7: update fields: %s", list(update_data.keys()))

    logger.info("RESOURCE UPDATE STEP 5/7: currency conversion if base_price present")
    if "base_price" in update_data:
        from app.core.currency.service import to_usd
        input_currency = update_data.pop("currency", None) or "USD"
        logger.info("Converting base_price %s %s to USD", update_data["base_price"], input_currency)
        update_data["base_price"] = await to_usd(update_data["base_price"], input_currency)
        update_data["currency"] = "USD"
        logger.info("Converted base_price to %s USD", update_data["base_price"])
    elif "currency" in update_data:
        logger.info("currency present without base_price — popping currency field")
        update_data.pop("currency")

    logger.info("RESOURCE UPDATE STEP 6/7: apply update_data and commit")
    for key, value in update_data.items():
        logger.debug("  set %s = %s", key, value)
        setattr(resource, key, value)
    resource.updated_at = datetime.now(UTC)
    resource.version += 1
    session.add(resource)
    await session.commit()
    await session.refresh(resource)
    logger.info("RESOURCE UPDATE STEP 6/7 OK — version=%s", resource.version)

    logger.info("RESOURCE UPDATE STEP 7/7: sync to Meilisearch")
    tenant_ctx = get_current_tenant()
    if tenant_ctx:
        rt_for_sync = await get_resource_type(session, resource.type_id)
        doc = build_document(
            resource.id, resource.name, resource.description,
            resource.location_lat, resource.location_lng, resource.location_address,
            resource.attributes, resource.base_price, resource.currency,
            resource.status, resource.rating_avg, resource.rating_count,
            rt_for_sync.slug, resource.created_at,
        )
        sync_resource(str(tenant_ctx.tenant.id), rt_for_sync.slug, doc)
        logger.info("RESOURCE UPDATE STEP 7/7 OK — synced to meilisearch")
    else:
        logger.info("RESOURCE UPDATE STEP 7/7: no tenant context — skipping meilisearch sync")

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

    rt_for_sync = await get_resource_type(session, resource.type_id)

    resource.status = "archived"
    resource.updated_at = datetime.now(UTC)
    session.add(resource)
    await session.commit()

    tenant_ctx = get_current_tenant()
    if tenant_ctx:
        remove_resource(str(tenant_ctx.tenant.id), rt_for_sync.slug, str(resource.id))


async def check_availability(
    session: AsyncSession,
    resource_id: uuid.UUID,
    start: datetime,
    end: datetime,
) -> tuple[bool, float | None]:
    resource = await get_resource(session, resource_id)
    rt = await get_resource_type(session, resource.type_id)

    effective_slot_config = resource.slot_config or rt.slot_config
    provider = get_availability_provider(rt.availability_model)
    errors = provider.validate_times(start, end, effective_slot_config)
    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    _validate_operating_hours(rt, start, end)

    buf = getattr(rt, "buffer_minutes", 0) or 0
    available = await provider.check(session, resource.id, start, end, buffer_minutes=buf)
    price = None
    if available:
        pricing = get_pricing_provider(rt.pricing_model)
        price = pricing.calculate(resource.base_price, start, end, rt.pricing_config)

    return available, price


async def check_schedule_availability(
    session: AsyncSession,
    resource_id: uuid.UUID,
    schedules: list[dict],
    availability_model: str,
) -> tuple[bool, list[dict]]:
    resource = await get_resource(session, resource_id)
    rt = await get_resource_type(session, resource.type_id)
    provider = get_availability_provider(availability_model)
    buf = getattr(rt, "buffer_minutes", 0) or 0
    schedule_states: list[dict] = []
    all_available = True

    for item in schedules:
        d = item["date"]
        if availability_model == "time_slot":
            st = item.get("start_time", "00:00")
            et = item.get("end_time", "23:59")
            start = datetime.strptime(f"{d} {st}", "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
            end = datetime.strptime(f"{d} {et}", "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
        else:
            start = datetime.strptime(f"{d} 00:00", "%Y-%m-%d %H:%M").replace(tzinfo=UTC)
            end = datetime.strptime(f"{d} 23:59", "%Y-%m-%d %H:%M").replace(tzinfo=UTC)

        available = await provider.check(session, resource.id, start, end, buffer_minutes=buf)
        if not available:
            all_available = False

        schedule_states.append({
            "date": d,
            "start_time": item.get("start_time"),
            "end_time": item.get("end_time"),
            "available": available,
        })

    return all_available, schedule_states


async def hold_resource(
    session: AsyncSession,
    resource_id: uuid.UUID,
    start: datetime,
    end: datetime,
    hold_minutes: int | None = None,
) -> tuple[str, datetime, float]:
    resource = await get_resource(session, resource_id)
    if resource.status != "active":
        raise HTTPException(status_code=400, detail="Resource is not active")

    rt = await get_resource_type(session, resource.type_id)

    if rt.hold_config is None:
        raise HTTPException(
            status_code=400,
            detail="This resource type does not support holds. Book directly.",
        )

    from app.domains.resources.schemas import HoldConfig
    hc = HoldConfig(**rt.hold_config)
    effective_minutes = hold_minutes if hold_minutes is not None else hc.to_minutes()
    effective_minutes = max(1, min(60, effective_minutes))

    provider = get_availability_provider(rt.availability_model)

    effective_slot_config = resource.slot_config or rt.slot_config
    errors = provider.validate_times(start, end, effective_slot_config)
    if errors:
        raise HTTPException(status_code=422, detail={"validation_errors": errors})

    _validate_operating_hours(rt, start, end)

    buf = getattr(rt, "buffer_minutes", 0) or 0
    try:
        result = await provider.hold(
            session, resource.id, start, end, hold_minutes=effective_minutes,
            buffer_minutes=buf,
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
    await session.commit()
    return True


# --- Resource Assignments ---

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


async def list_availability_slots(
    session: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    resource_type_id: uuid.UUID | None = None,
    resource_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    scope_owner_ids: list[uuid.UUID] | None = None,
    offset: int = 0,
    limit: int = 100,
) -> list[dict]:
    from sqlalchemy import or_, select as sa_select
    from app.domains.bookings.models import Booking
    from app.core.auth.models import User

    stmt = (
        sa_select(
            ResourceAvailability.id,
            ResourceAvailability.resource_id,
            Resource.name.label("resource_name"),
            ResourceType.name.label("resource_type_name"),
            ResourceAvailability.start_time,
            ResourceAvailability.end_time,
            ResourceAvailability.status,
            ResourceAvailability.hold_token,
            ResourceAvailability.hold_expires,
            ResourceAvailability.booking_id,
            User.full_name.label("customer_name"),
        )
        .join(Resource, ResourceAvailability.resource_id == Resource.id)
        .join(ResourceType, Resource.type_id == ResourceType.id)
        .outerjoin(Booking, ResourceAvailability.booking_id == Booking.id)
        .outerjoin(User, Booking.user_id == User.id)
        .where(
            ResourceAvailability.start_time < end_date,
            ResourceAvailability.end_time > start_date,
        )
    )
    if search:
        stmt = stmt.where(
            or_(
                Resource.name.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )
    if resource_type_id:
        stmt = stmt.where(Resource.type_id == resource_type_id)
    if resource_id:
        stmt = stmt.where(ResourceAvailability.resource_id == resource_id)
    if status_filter:
        if status_filter == "active":
            stmt = stmt.where(
                ResourceAvailability.status == "held",
                ResourceAvailability.hold_expires > datetime.now(UTC),
            )
        else:
            stmt = stmt.where(ResourceAvailability.status == status_filter)
    if scope_owner_ids is not None:
        stmt = stmt.where(Resource.owner_id.in_(scope_owner_ids))

    stmt = stmt.offset(offset).limit(limit).order_by(
        Resource.name, ResourceAvailability.start_time
    )
    result = await session.exec(stmt)
    rows = []
    for row in result.all():
        rows.append({
            "id": row.id,
            "resource_id": row.resource_id,
            "resource_name": row.resource_name,
            "resource_type_name": row.resource_type_name,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "status": row.status,
            "hold_token": row.hold_token,
            "hold_expires": row.hold_expires,
            "booking_id": row.booking_id,
            "customer_name": row.customer_name,
        })
    return rows
