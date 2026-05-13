# Implementation: Domain-Based Tenant Resolution

## Step 1: Create `backend/app/core/tenancy/router.py` (NEW FILE)

```python
from fastapi import APIRouter, Query
from sqlmodel import select

from app import database as db_module
from app.core.tenancy.models import Tenant, TenantDomain

router = APIRouter(prefix="/api/tenancy", tags=["tenancy"])


@router.get("/resolve")
async def resolve_tenant(domain: str = Query(...)):
    async with db_module.async_session_factory() as session:
        result = await session.exec(select(TenantDomain).where(TenantDomain.domain == domain))
        tenant_domain = result.first()
        if tenant_domain is None:
            return None

        result = await session.exec(
            select(Tenant).where(Tenant.id == tenant_domain.tenant_id, Tenant.is_active.is_(True))
        )
        tenant = result.first()
        if tenant is None:
            return None

        return {
            "tenant_id": str(tenant.id),
            "slug": tenant.slug,
            "schema_name": tenant.schema_name,
            "name": tenant.name,
        }
```

## Step 2: Update `backend/app/main.py`

**Add import** (after line 16, with other tenancy imports):
```python
from app.core.tenancy.router import router as tenancy_router
```

**Register router** (after line 43, before `auth_router`):
```python
app.include_router(tenancy_router)
```

## Step 3: Update `backend/app/core/tenancy/middleware.py`

**Line 12**: Add `/api/tenancy/resolve` to `TENANT_FREE_PATHS`:
```python
TENANT_FREE_PATHS = {"/api/health", "/api/docs", "/api/openapi.json", "/api/redoc", "/api/tenancy/resolve"}
```

**Line 18**: Remove the debug print statement:
```python
# DELETE THIS LINE: print('logging inside the dispatcher for tenantmiddleware', request )
```

## Step 4: Update `frontend/src/components/tenant-initializer.tsx`

Replace entire file with:
```tsx
"use client";

import { useEffect } from "react";
import { useTenantStore } from "@/lib/tenant-store";

async function resolveTenantByDomain(domain: string) {
  const res = await fetch(`/api/tenancy/resolve?domain=${encodeURIComponent(domain)}`);
  if (!res.ok) return null;
  const data = await res.json();
  return data;
}

export function TenantInitializer() {
  const setSlug = useTenantStore((s) => s.setSlug);

  useEffect(() => {
    const host = window.location.hostname;
    const isLocalhost = host === "localhost" || host === "127.0.0.1";

    async function init() {
      // 1. Try domain-based resolution
      const resolved = await resolveTenantByDomain(host);
      if (resolved?.slug) {
        setSlug(resolved.slug);
        return;
      }

      // 2. Fallback: path-based extraction for localhost dev
      if (isLocalhost) {
        const match = window.location.pathname.match(/^\/t\/([^/]+)/);
        if (match) {
          setSlug(match[1]);
        }
      }
    }

    init();
  }, [setSlug]);

  return null;
}
```

## Step 5: Insert Dev Domain into Database

Run this in your postgres container:
```bash
docker compose exec postgres psql -U rentmanager -d rentmanager -c "
INSERT INTO tenant_domains (id, tenant_id, domain, is_primary, is_verified, created_at)
VALUES (gen_random_uuid(), '12c2637f-968f-4bb8-8c70-5ab3bcc3e3a5', 'localhost', true, true, NOW())
ON CONFLICT (domain) DO NOTHING;
"
```

## Step 6: Rebuild Backend

```bash
docker compose up -d --build backend
```

## Verification

1. Check logs: `docker compose logs -f backend` — should see startup without errors
2. Test resolve endpoint: `curl "http://localhost:8000/api/tenancy/resolve?domain=localhost"` — should return tenant data
3. Navigate to `http://localhost:3000` — frontend should resolve tenant automatically and set `X-Tenant-ID` header
4. Login should work without CORS errors
