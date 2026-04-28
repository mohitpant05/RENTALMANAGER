from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.search.query import execute_search
from app.core.search.schemas import SearchRequest, SearchResponse
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_resources(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    try:
        result = execute_search(str(tenant_ctx.tenant.id), request)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Search service error: {e}")

    return result
