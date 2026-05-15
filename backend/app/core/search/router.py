from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.search.query import execute_search
from app.core.search.schemas import SearchHit, SearchRequest, SearchResponse
from app.core.tenancy.context import get_current_tenant
from app.database import get_db
from app.domains.resources.models import ResourceType

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_resources(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    tenant_id = str(tenant_ctx.tenant.id)

    if request.resource_type_slug:
        try:
            return execute_search(tenant_id, request)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Search service error: {e}")

    result = await session.exec(
        select(ResourceType).where(
            ResourceType.is_active.is_(True),
            ResourceType.role.in_(["primary", "standalone"]),
        )
    )
    types = list(result.all())

    all_hits: list[SearchHit] = []
    total_estimated = 0
    total_time = 0

    for rt in types:
        type_request = SearchRequest(
            q=request.q,
            resource_type_slug=rt.slug,
            filters=request.filters,
            geo_lat=request.geo_lat,
            geo_lng=request.geo_lng,
            geo_radius_km=request.geo_radius_km,
            sort_by=request.sort_by,
            sort_order=request.sort_order,
            offset=0,
            limit=request.limit,
        )
        try:
            res = execute_search(tenant_id, type_request)
            all_hits.extend(res.hits)
            total_estimated += res.estimated_total_hits
            total_time = max(total_time, res.processing_time_ms)
        except Exception:
            continue

    if request.sort_by == "base_price":
        reverse = request.sort_order == "desc"
        all_hits.sort(key=lambda h: h.base_price, reverse=reverse)
    elif request.sort_by == "rating_avg":
        reverse = request.sort_order == "desc"
        all_hits.sort(key=lambda h: h.rating_avg, reverse=reverse)

    start = request.offset
    end = start + request.limit
    paged = all_hits[start:end]

    return SearchResponse(
        hits=paged,
        query=request.q,
        processing_time_ms=total_time,
        estimated_total_hits=total_estimated,
        offset=request.offset,
        limit=request.limit,
    )
