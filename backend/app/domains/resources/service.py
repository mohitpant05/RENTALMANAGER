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
