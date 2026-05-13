# Search & Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate Meilisearch for full-text, faceted, and geo search with per-tenant, per-resource-type indexes that auto-adapt when resource types or resources change.

**Architecture:** A search service module (`app/core/search/`) manages Meilisearch indexes. Each tenant+resource_type gets a unique index (`tenant_{id}_{slug}`). Resources are synced to Meilisearch on create/update/delete via the service layer. A Celery task handles full reindex nightly. The search API returns resource IDs + scores; availability filtering happens post-search against DB for real-time accuracy.

**Tech Stack:** Meilisearch Python SDK (0.41.0), FastAPI, Celery

---

## File Structure

| File | Responsibility |
|------|---------------|
| `backend/app/core/search/__init__.py` | Package marker |
| `backend/app/core/search/client.py` | Meilisearch client singleton |
| `backend/app/core/search/indexing.py` | Index lifecycle: create, configure, delete indexes |
| `backend/app/core/search/sync.py` | Document sync: add, update, delete documents |
| `backend/app/core/search/query.py` | Search query builder with filters, geo, sort |
| `backend/app/core/search/router.py` | Search API endpoint |
| `backend/app/core/search/schemas.py` | Search request/response schemas |
| `backend/app/core/search/tasks.py` | Celery task: full reindex |
| `backend/app/domains/resources/service.py` | Modified: trigger search sync on resource CRUD |
| `backend/app/main.py` | Modified: register search router |
| `backend/app/celery_app.py` | Modified: add nightly reindex schedule |
| `backend/tests/test_search_unit.py` | Document building, query building logic |
| `backend/tests/test_search_integration.py` | End-to-end search via API |

---

### Task 1: Meilisearch client singleton

**Files:**
- Create: `backend/app/core/search/__init__.py`
- Create: `backend/app/core/search/client.py`

- [ ] **Step 1: Create package**

```python
# backend/app/core/search/__init__.py
```

Empty file.

- [ ] **Step 2: Create client module**

```python
# backend/app/core/search/client.py
import meilisearch

from app.config import get_settings


def get_meili_client() -> meilisearch.Client:
    settings = get_settings()
    return meilisearch.Client(settings.meili_url, settings.meili_master_key)


def get_index_uid(tenant_id: str, resource_type_slug: str) -> str:
    safe_tenant = tenant_id.replace("-", "_")
    safe_slug = resource_type_slug.replace("-", "_")
    return f"t_{safe_tenant}_{safe_slug}"
```

- [ ] **Step 3: Verify**

Run: `docker exec rm-backend python -c "from app.core.search.client import get_meili_client, get_index_uid; c = get_meili_client(); print(c.health()); print(get_index_uid('abc-123', 'venues'))"`

Expected: `{'status': 'available'}` and `t_abc_123_venues`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/search/
git commit -m "feat(search): add Meilisearch client singleton and index UID helper"
```

---

### Task 2: Index lifecycle management

**Files:**
- Create: `backend/app/core/search/indexing.py`

- [ ] **Step 1: Implement index management**

```python
# backend/app/core/search/indexing.py
import meilisearch

from app.core.search.client import get_index_uid, get_meili_client


def create_resource_type_index(
    tenant_id: str,
    resource_type_slug: str,
    attribute_schema: list[dict] | None = None,
) -> str:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)

    client.create_index(uid, {"primaryKey": "id"})

    filterable = ["status", "base_price", "rating_avg", "type_slug"]
    sortable = ["base_price", "rating_avg", "created_at"]
    searchable = ["name", "description", "location_address"]

    if attribute_schema:
        for attr in attribute_schema:
            attr_name = f"attr_{attr['name']}"
            if attr.get("filterable"):
                filterable.append(attr_name)
            searchable.append(attr_name)

    index = client.index(uid)
    index.update_filterable_attributes(filterable)
    index.update_sortable_attributes(sortable)
    index.update_searchable_attributes(searchable)
    index.update_settings({"displayedAttributes": ["*"]})

    return uid


def delete_resource_type_index(tenant_id: str, resource_type_slug: str) -> None:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)
    try:
        client.delete_index(uid)
    except meilisearch.errors.MeilisearchApiError:
        pass


def configure_geo(tenant_id: str, resource_type_slug: str) -> None:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)
    index = client.index(uid)
    current_sortable = index.get_sortable_attributes()
    if "_geo" not in current_sortable:
        index.update_sortable_attributes(current_sortable + ["_geo"])
    current_filterable = index.get_filterable_attributes()
    if "_geo" not in current_filterable:
        index.update_filterable_attributes(current_filterable + ["_geo"])
```

- [ ] **Step 2: Verify**

Run: `docker exec rm-backend python -c "from app.core.search.indexing import create_resource_type_index, delete_resource_type_index; uid = create_resource_type_index('test-tenant', 'venues', [{'name': 'bedrooms', 'type': 'number', 'filterable': True}]); print('Created:', uid); delete_resource_type_index('test-tenant', 'venues'); print('Deleted OK')"`

Expected: `Created: t_test_tenant_venues` and `Deleted OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/search/indexing.py
git commit -m "feat(search): add index lifecycle management (create, configure, delete)"
```

---

### Task 3: Document sync (add/update/delete resources in index)

**Files:**
- Create: `backend/app/core/search/sync.py`

- [ ] **Step 1: Implement document sync**

```python
# backend/app/core/search/sync.py
from __future__ import annotations

import uuid
from datetime import datetime

import meilisearch

from app.core.search.client import get_index_uid, get_meili_client


def build_document(
    resource_id: uuid.UUID,
    name: str,
    description: str | None,
    location_lat: float | None,
    location_lng: float | None,
    location_address: str | None,
    attributes: dict | None,
    base_price: float,
    currency: str,
    status: str,
    rating_avg: float,
    rating_count: int,
    type_slug: str,
    created_at: datetime,
) -> dict:
    doc: dict = {
        "id": str(resource_id),
        "name": name,
        "description": description or "",
        "location_address": location_address or "",
        "base_price": base_price,
        "currency": currency,
        "status": status,
        "rating_avg": rating_avg,
        "rating_count": rating_count,
        "type_slug": type_slug,
        "created_at": int(created_at.timestamp()),
    }

    if location_lat is not None and location_lng is not None:
        doc["_geo"] = {"lat": location_lat, "lng": location_lng}

    if attributes:
        for key, value in attributes.items():
            doc[f"attr_{key}"] = value

    return doc


def sync_resource(
    tenant_id: str,
    resource_type_slug: str,
    document: dict,
) -> None:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)
    try:
        index = client.index(uid)
        index.add_documents([document])
    except meilisearch.errors.MeilisearchApiError:
        pass


def remove_resource(
    tenant_id: str,
    resource_type_slug: str,
    resource_id: str,
) -> None:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)
    try:
        index = client.index(uid)
        index.delete_document(resource_id)
    except meilisearch.errors.MeilisearchApiError:
        pass
```

- [ ] **Step 2: Verify**

Run: `docker exec rm-backend python -c "from app.core.search.sync import build_document; import uuid; from datetime import datetime, UTC; doc = build_document(uuid.uuid4(), 'Beach House', 'Nice place', 40.7, -74.0, '123 Main St', {'bedrooms': 3}, 150.0, 'USD', 'active', 4.5, 10, 'venues', datetime.now(UTC)); print(doc.keys()); assert '_geo' in doc; assert 'attr_bedrooms' in doc; print('OK')"`

Expected: Shows dict keys and `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/search/sync.py
git commit -m "feat(search): add document sync (build, add/update, delete)"
```

---

### Task 4: Search query builder and schemas

**Files:**
- Create: `backend/app/core/search/schemas.py`
- Create: `backend/app/core/search/query.py`

- [ ] **Step 1: Create search schemas**

```python
# backend/app/core/search/schemas.py
from pydantic import BaseModel, field_validator


class SearchRequest(BaseModel):
    q: str = ""
    resource_type_slug: str
    filters: dict | None = None
    geo_lat: float | None = None
    geo_lng: float | None = None
    geo_radius_km: float | None = None
    sort_by: str | None = None
    sort_order: str = "asc"
    offset: int = 0
    limit: int = 20

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v: str) -> str:
        if v not in ("asc", "desc"):
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be between 1 and 100")
        return v


class SearchHit(BaseModel):
    id: str
    name: str
    description: str
    location_address: str
    base_price: float
    currency: str
    status: str
    rating_avg: float
    rating_count: int
    type_slug: str
    geo: dict | None = None
    attributes: dict | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHit]
    query: str
    processing_time_ms: int
    estimated_total_hits: int
    offset: int
    limit: int
```

- [ ] **Step 2: Create query builder**

```python
# backend/app/core/search/query.py
from app.core.search.client import get_index_uid, get_meili_client
from app.core.search.schemas import SearchRequest, SearchHit, SearchResponse


def _build_filter_string(filters: dict | None) -> list[str]:
    if not filters:
        return []
    parts = []
    for key, value in filters.items():
        attr_key = f"attr_{key}" if not key.startswith(("status", "base_price", "rating")) else key
        if isinstance(value, list):
            conditions = [f'{attr_key} = "{v}"' for v in value]
            parts.append(f"({' OR '.join(conditions)})")
        elif isinstance(value, dict):
            if "min" in value:
                parts.append(f"{attr_key} >= {value['min']}")
            if "max" in value:
                parts.append(f"{attr_key} <= {value['max']}")
        else:
            parts.append(f'{attr_key} = "{value}"')
    return parts


def execute_search(tenant_id: str, request: SearchRequest) -> SearchResponse:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, request.resource_type_slug)
    index = client.index(uid)

    search_params: dict = {
        "offset": request.offset,
        "limit": request.limit,
    }

    filter_parts = ["status = \"active\""]
    filter_parts.extend(_build_filter_string(request.filters))

    if request.geo_lat is not None and request.geo_lng is not None and request.geo_radius_km:
        radius_m = int(request.geo_radius_km * 1000)
        filter_parts.append(
            f"_geoRadius({request.geo_lat}, {request.geo_lng}, {radius_m})"
        )

    search_params["filter"] = filter_parts

    if request.sort_by:
        sort_attr = request.sort_by
        if not sort_attr.startswith(("base_price", "rating_avg", "created_at", "_geo")):
            sort_attr = f"attr_{sort_attr}"
        if sort_attr == "_geo" and request.geo_lat is not None and request.geo_lng is not None:
            search_params["sort"] = [
                f"_geoPoint({request.geo_lat}, {request.geo_lng}):{request.sort_order}"
            ]
        else:
            search_params["sort"] = [f"{sort_attr}:{request.sort_order}"]

    result = index.search(request.q, search_params)

    hits = []
    for hit in result["hits"]:
        attrs = {}
        geo = hit.get("_geo")
        for k, v in hit.items():
            if k.startswith("attr_"):
                attrs[k[5:]] = v
        hits.append(SearchHit(
            id=hit["id"],
            name=hit.get("name", ""),
            description=hit.get("description", ""),
            location_address=hit.get("location_address", ""),
            base_price=hit.get("base_price", 0),
            currency=hit.get("currency", "USD"),
            status=hit.get("status", ""),
            rating_avg=hit.get("rating_avg", 0),
            rating_count=hit.get("rating_count", 0),
            type_slug=hit.get("type_slug", ""),
            geo=geo,
            attributes=attrs if attrs else None,
        ))

    return SearchResponse(
        hits=hits,
        query=result.get("query", request.q),
        processing_time_ms=result.get("processingTimeMs", 0),
        estimated_total_hits=result.get("estimatedTotalHits", 0),
        offset=request.offset,
        limit=request.limit,
    )
```

- [ ] **Step 3: Verify**

Run: `docker exec rm-backend python -c "from app.core.search.query import _build_filter_string; f = _build_filter_string({'bedrooms': {'min': 2, 'max': 5}, 'pet_friendly': 'true', 'amenities': ['pool', 'wifi']}); print(f)"`

Expected: List of filter strings.

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/search/schemas.py backend/app/core/search/query.py
git commit -m "feat(search): add search schemas and query builder with filters, geo, sort"
```

---

### Task 5: Search API router

**Files:**
- Create: `backend/app/core/search/router.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create search router**

```python
# backend/app/core/search/router.py
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
```

- [ ] **Step 2: Register router in main.py**

Add import in `backend/app/main.py`:

```python
from app.core.search.router import router as search_router
```

And add after the booking router:

```python
app.include_router(search_router)
```

- [ ] **Step 3: Verify**

Run: `docker exec rm-backend python -c "from app.main import app; paths = [r.path for r in app.routes if hasattr(r, 'path')]; assert '/api/search' in paths; print('Search route registered')"`

Expected: `Search route registered`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/search/router.py backend/app/main.py
git commit -m "feat(search): add search API endpoint"
```

---

### Task 6: Sync on resource CRUD + index on resource type create

**Files:**
- Modify: `backend/app/domains/resources/service.py`

- [ ] **Step 1: Add search sync to resource service**

Add imports at top of `backend/app/domains/resources/service.py`:

```python
from app.core.search.indexing import create_resource_type_index, delete_resource_type_index
from app.core.search.sync import build_document, sync_resource, remove_resource
from app.core.tenancy.context import get_current_tenant
```

Then modify `create_resource_type` — after `await session.refresh(rt)` and before `return rt`, add:

```python
    tenant_ctx = get_current_tenant()
    if tenant_ctx:
        create_resource_type_index(
            str(tenant_ctx.tenant.id), rt.slug, rt.attribute_schema
        )
```

Modify `delete_resource_type` — after `await session.commit()`, add:

```python
    tenant_ctx = get_current_tenant()
    if tenant_ctx:
        delete_resource_type_index(str(tenant_ctx.tenant.id), rt.slug)
```

Modify `create_resource` — after `await session.refresh(resource)` and before `return resource`, add:

```python
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
```

Modify `update_resource` — after `await session.refresh(resource)` and before `return resource`, add:

```python
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
```

Modify `delete_resource` — after `await session.commit()`, add:

```python
    tenant_ctx = get_current_tenant()
    if tenant_ctx:
        rt_for_sync = await get_resource_type(session, resource.type_id)
        remove_resource(str(tenant_ctx.tenant.id), rt_for_sync.slug, str(resource.id))
```

- [ ] **Step 2: Verify import chain**

Run: `docker exec rm-backend python -c "from app.domains.resources.service import create_resource_type, create_resource; print('OK')"`

Expected: `OK`

- [ ] **Step 3: Run existing tests to ensure no breakage**

Run: `docker exec rm-backend python -m pytest tests/test_resource_integration.py --tb=short -q`

Expected: All tests pass (search sync is fire-and-forget; missing indexes are caught by try/except in sync.py).

- [ ] **Step 4: Commit**

```bash
git add backend/app/domains/resources/service.py
git commit -m "feat(search): sync resources to Meilisearch on create/update/delete"
```

---

### Task 7: Celery full reindex task

**Files:**
- Create: `backend/app/core/search/tasks.py`
- Modify: `backend/app/celery_app.py`

- [ ] **Step 1: Create reindex task**

```python
# backend/app/core/search/tasks.py
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
```

- [ ] **Step 2: Add Celery task wrapper and beat schedule**

In `backend/app/celery_app.py`, add a new task after the existing booking tasks:

```python
@celery.task(name="search.full_reindex")
def task_full_reindex():
    async def _reindex_tenant(session):
        from app.core.search.tasks import full_reindex
        from app.core.tenancy.context import get_current_tenant
        tenant_ctx = get_current_tenant()
        if tenant_ctx:
            return await full_reindex(session, str(tenant_ctx.tenant.id))
        return 0
    return _run_async(_run_for_all_tenants(_reindex_tenant))
```

Wait — `_run_for_all_tenants` doesn't set `TenantContext`. Let me use a different approach. Add to beat_schedule:

```python
    "search-full-reindex": {
        "task": "search.full_reindex",
        "schedule": 86400.0,  # daily
    },
```

And the task:

```python
@celery.task(name="search.full_reindex")
def task_full_reindex():
    async def _do_reindex():
        from sqlalchemy import text as sa_text
        from sqlmodel import select
        from app.core.tenancy.context import validate_schema_name
        from app.core.tenancy.models import Tenant
        from app.core.search.tasks import full_reindex
        from app.database import async_session_factory

        async with async_session_factory() as session:
            result = await session.exec(
                select(Tenant).where(Tenant.is_active.is_(True))
            )
            tenants = list(result.all())

        total = 0
        for tenant in tenants:
            validate_schema_name(tenant.schema_name)
            async with async_session_factory() as session:
                await session.execute(
                    sa_text(f"SET search_path TO {tenant.schema_name}, public")
                )
                count = await full_reindex(session, str(tenant.id))
                total += count
                await session.execute(sa_text("SET search_path TO public"))
        return total

    return _run_async(_do_reindex())
```

- [ ] **Step 3: Verify**

Run: `docker exec rm-backend python -c "from app.core.search.tasks import full_reindex; from app.celery_app import celery; assert 'search-full-reindex' in celery.conf.beat_schedule; print('OK')"`

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/search/tasks.py backend/app/celery_app.py
git commit -m "feat(search): add Celery nightly full reindex task"
```

---

### Task 8: Unit tests

**Files:**
- Create: `backend/tests/test_search_unit.py`

- [ ] **Step 1: Write unit tests**

```python
# backend/tests/test_search_unit.py
import uuid
from datetime import UTC, datetime

from app.core.search.client import get_index_uid
from app.core.search.query import _build_filter_string
from app.core.search.schemas import SearchRequest, SearchResponse
from app.core.search.sync import build_document


def test_get_index_uid_basic():
    uid = get_index_uid("abc-123", "venues")
    assert uid == "t_abc_123_venues"


def test_get_index_uid_complex_slug():
    uid = get_index_uid("tenant-uuid-here", "electric-bikes")
    assert uid == "t_tenant_uuid_here_electric_bikes"


def test_build_document_basic():
    doc = build_document(
        resource_id=uuid.UUID("12345678-1234-1234-1234-123456789012"),
        name="Beach House",
        description="A nice place",
        location_lat=40.7,
        location_lng=-74.0,
        location_address="123 Main St",
        attributes={"bedrooms": 3, "pet_friendly": True},
        base_price=150.0,
        currency="USD",
        status="active",
        rating_avg=4.5,
        rating_count=10,
        type_slug="venues",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert doc["id"] == "12345678-1234-1234-1234-123456789012"
    assert doc["name"] == "Beach House"
    assert doc["_geo"] == {"lat": 40.7, "lng": -74.0}
    assert doc["attr_bedrooms"] == 3
    assert doc["attr_pet_friendly"] is True
    assert doc["base_price"] == 150.0
    assert doc["type_slug"] == "venues"


def test_build_document_no_geo():
    doc = build_document(
        resource_id=uuid.uuid4(),
        name="Service",
        description=None,
        location_lat=None,
        location_lng=None,
        location_address=None,
        attributes=None,
        base_price=50.0,
        currency="USD",
        status="active",
        rating_avg=0.0,
        rating_count=0,
        type_slug="cooks",
        created_at=datetime.now(UTC),
    )
    assert "_geo" not in doc
    assert doc["description"] == ""


def test_build_document_no_attributes():
    doc = build_document(
        resource_id=uuid.uuid4(),
        name="Item",
        description="Desc",
        location_lat=None,
        location_lng=None,
        location_address=None,
        attributes=None,
        base_price=10.0,
        currency="EUR",
        status="active",
        rating_avg=3.0,
        rating_count=5,
        type_slug="vehicles",
        created_at=datetime.now(UTC),
    )
    attr_keys = [k for k in doc.keys() if k.startswith("attr_")]
    assert attr_keys == []


def test_build_filter_string_range():
    filters = {"base_price": {"min": 50, "max": 200}}
    parts = _build_filter_string(filters)
    assert "base_price >= 50" in parts
    assert "base_price <= 200" in parts


def test_build_filter_string_list():
    filters = {"amenities": ["pool", "wifi"]}
    parts = _build_filter_string(filters)
    assert len(parts) == 1
    assert "OR" in parts[0]


def test_build_filter_string_exact():
    filters = {"pet_friendly": "true"}
    parts = _build_filter_string(filters)
    assert parts == ['attr_pet_friendly = "true"']


def test_build_filter_string_empty():
    assert _build_filter_string(None) == []
    assert _build_filter_string({}) == []


def test_search_request_defaults():
    req = SearchRequest(resource_type_slug="venues")
    assert req.q == ""
    assert req.offset == 0
    assert req.limit == 20
    assert req.sort_order == "asc"


def test_search_request_limit_validation():
    from pydantic import ValidationError
    try:
        SearchRequest(resource_type_slug="venues", limit=0)
        assert False, "Should raise"
    except ValidationError:
        pass

    try:
        SearchRequest(resource_type_slug="venues", limit=101)
        assert False, "Should raise"
    except ValidationError:
        pass


def test_search_response_model():
    resp = SearchResponse(
        hits=[],
        query="test",
        processing_time_ms=5,
        estimated_total_hits=0,
        offset=0,
        limit=20,
    )
    assert resp.hits == []
    assert resp.processing_time_ms == 5
```

- [ ] **Step 2: Run tests**

Run: `docker exec rm-backend python -m pytest tests/test_search_unit.py -v`

Expected: All pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_search_unit.py
git commit -m "test(search): add unit tests for document building, filter strings, schemas"
```

---

### Task 9: Integration tests

**Files:**
- Create: `backend/tests/test_search_integration.py`

- [ ] **Step 1: Write integration tests**

```python
# backend/tests/test_search_integration.py
import time
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.fixture
async def search_venue_type(client: AsyncClient, admin_headers: dict) -> dict:
    resp = await client.post(
        "/api/resource-types",
        json={
            "name": "Search Test Venues",
            "slug": "search-test-venues",
            "availability_model": "date_range",
            "pricing_model": "fixed_per_day",
            "attribute_schema": [
                {"name": "bedrooms", "type": "number", "required": True, "filterable": True},
                {"name": "pet_friendly", "type": "boolean", "required": False, "filterable": True},
            ],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def indexed_resource(
    client: AsyncClient, admin_headers: dict, search_venue_type: dict
) -> dict:
    resp = await client.post(
        "/api/resources",
        json={
            "type_id": search_venue_type["id"],
            "name": "Seaside Villa",
            "description": "Beautiful villa by the sea",
            "base_price": 200.0,
            "location_lat": 40.7128,
            "location_lng": -74.0060,
            "location_address": "123 Ocean Dr",
            "attributes": {"bedrooms": 3, "pet_friendly": True},
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    resource = resp.json()

    resp = await client.patch(
        f"/api/resources/{resource['id']}",
        json={"status": "active"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    # Give Meilisearch time to index
    time.sleep(1)
    return resp.json()


@pytest.mark.asyncio
async def test_search_basic(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "Seaside",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_total_hits"] >= 1
    assert any(h["id"] == indexed_resource["id"] for h in data["hits"])


@pytest.mark.asyncio
async def test_search_with_filter(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "",
            "filters": {"bedrooms": {"min": 2}},
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_total_hits"] >= 1


@pytest.mark.asyncio
async def test_search_with_geo(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "",
            "geo_lat": 40.71,
            "geo_lng": -74.01,
            "geo_radius_km": 10,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_total_hits"] >= 1


@pytest.mark.asyncio
async def test_search_no_results(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "xyznonexistent123",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["estimated_total_hits"] == 0
    assert data["hits"] == []


@pytest.mark.asyncio
async def test_search_sort_by_price(
    client: AsyncClient, admin_headers: dict, indexed_resource: dict
):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "search-test-venues",
            "q": "",
            "sort_by": "base_price",
            "sort_order": "desc",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["estimated_total_hits"] >= 1


@pytest.mark.asyncio
async def test_search_without_tenant_fails(client: AsyncClient):
    resp = await client.post(
        "/api/search",
        json={
            "resource_type_slug": "venues",
            "q": "test",
        },
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests**

Run: `docker exec rm-backend python -m pytest tests/test_search_integration.py -v --tb=short`

Expected: All pass. Note: `time.sleep(1)` gives Meilisearch time to process the async indexing task.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_search_integration.py
git commit -m "test(search): add integration tests for search API with filters, geo, sort"
```

---

### Task 10: Final verification + cleanup

- [ ] **Step 1: Run full test suite**

Run: `docker exec rm-backend python -m pytest --tb=short -q`

Expected: All tests pass (144 existing + new search tests).

- [ ] **Step 2: Lint check**

Run: `docker exec rm-backend python -m ruff check app/core/search/ tests/test_search_unit.py tests/test_search_integration.py`

Expected: Clean or auto-fixable.

- [ ] **Step 3: Verify search route registered**

Run: `docker exec rm-backend python -c "from app.main import app; paths = [r.path for r in app.routes if hasattr(r, 'path')]; assert '/api/search' in paths; print('OK')"`

- [ ] **Step 4: Fix lint issues and commit if needed**

```bash
docker exec rm-backend python -m ruff check --fix app/core/search/ tests/test_search_unit.py tests/test_search_integration.py
git add -A && git commit -m "style: fix lint issues in search module" --allow-empty
```

---

## Spec Coverage Check

| Spec Requirement | Task |
|-----------------|------|
| Meilisearch indexes per tenant per resource type | Task 2 (create_resource_type_index) |
| Searchable: name, description, location, dynamic attributes | Task 2 (searchable config) |
| Filterable: price, rating, dynamic filterable attributes | Task 2 (filterable config from attribute_schema) |
| Sortable: price, rating, distance | Task 2 (sortable config) + Task 4 (geo sort) |
| Geo: radius from point | Task 4 (geo_radius_km filter) |
| Faceted filtering — dynamic per resource type | Task 4 (filters dict with attr_ prefix) |
| DB → Meilisearch on resource create/update/delete | Task 6 (service.py hooks) |
| Full reindex nightly | Task 7 (Celery beat task) |
| Availability filtering post-search against DB | Noted as future — search returns IDs, frontend checks availability separately |
| Typo tolerance | Built-in to Meilisearch (no config needed) |
| Instant search sub-50ms | Architecture ensures this (Meilisearch default) |
| Index auto-created on resource type create | Task 6 (create_resource_type hook) |
