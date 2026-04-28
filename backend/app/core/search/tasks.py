from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.search.indexing import create_resource_type_index
from app.core.search.sync import build_document, sync_resource
from app.domains.resources.models import Resource, ResourceType


async def full_reindex(session: AsyncSession, tenant_id: str) -> int:
    result = await session.exec(
        select(ResourceType).where(ResourceType.is_active.is_(True))
    )
    resource_types = list(result.all())

    total = 0
    for rt in resource_types:
        create_resource_type_index(tenant_id, rt.slug, rt.attribute_schema)

        result = await session.exec(
            select(Resource).where(
                Resource.type_id == rt.id,
                Resource.status == "active",
            )
        )
        resources = list(result.all())

        for resource in resources:
            doc = build_document(
                resource.id, resource.name, resource.description,
                resource.location_lat, resource.location_lng, resource.location_address,
                resource.attributes, resource.base_price, resource.currency,
                resource.status, resource.rating_avg, resource.rating_count,
                rt.slug, resource.created_at,
            )
            sync_resource(tenant_id, rt.slug, doc)
            total += 1

    return total
