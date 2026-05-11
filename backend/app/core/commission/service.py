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
