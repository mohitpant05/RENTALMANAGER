import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

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

    input_currency = data.currency or "USD"
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
    )
    session.add(resource)
    await session.commit()
    await session.refresh(resource)

    tenant_ctx = get_current_tenant()
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
    if "base_price" in update_data:
        from app.core.currency.service import to_usd
        input_currency = update_data.pop("currency", None) or "USD"
        update_data["base_price"] = await to_usd(update_data["base_price"], input_currency)
        update_data["currency"] = "USD"
    elif "currency" in update_data:
        update_data.pop("currency")
    for key, value in update_data.items():
        setattr(resource, key, value)
    resource.updated_at = datetime.now(UTC)
    resource.version += 1
    session.add(resource)
    await session.commit()
    await session.refresh(resource)

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
