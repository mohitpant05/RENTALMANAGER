import math
import uuid

from sqlmodel import select
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

    result: dict[str, dict] = {}

    for addon_type in addon_types:
        items: list[dict] = []
        assigned_ids_for_type: set[uuid.UUID] = set()

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
                "slot_config": resource.slot_config,
            })
            assigned_ids_for_type.add(resource.id)

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
                    "slot_config": resource.slot_config,
                })

            non_assigned = [i for i in items if not i["is_assigned"]]
            assigned_items = [i for i in items if i["is_assigned"]]
            non_assigned.sort(key=lambda x: x["distance_km"] or 999999)
            items = assigned_items + non_assigned

        if items:
            result[addon_type.slug] = {
                "type_name": addon_type.name,
                "type_slug": addon_type.slug,
                "availability_model": addon_type.availability_model,
                "pricing_model": addon_type.pricing_model,
                "slot_config": addon_type.slot_config,
                "resources": items,
            }

    return result
