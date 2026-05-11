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
    result = await session.exec(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.first()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    config = await resolve_commission(session, resource_id)
    breakdown = calculate_breakdown(amount, resource.currency, config)
    return {
        "amount": amount,
        "currency": resource.currency,
        "config": config.model_dump() if config else None,
        **breakdown,
    }
