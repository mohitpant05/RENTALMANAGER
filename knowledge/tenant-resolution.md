# Tenant Resolution — End-to-End

How tenant ID is determined from an HTTP request, covering both frontend and backend.

## Overview

```
Browser Request
  │
  ├─ Frontend (Next.js middleware + TenantInitializer)
  │   → extracts tenant slug from URL/subdomain
  │   → stores in Zustand tenant-store
  │   → API interceptor injects X-Tenant-ID header on every API call
  │
  └─ Backend (TenantMiddleware)
      → 3-step resolution waterfall
      → sets TenantContext via ContextVar
      → DB session auto-sets search_path
```

## Backend Resolution (`backend/app/core/tenancy/middleware.py`)

### Exempt Paths (no tenant required)
- `/api/health`, `/api/docs`, `/api/openapi.json`, `/api/redoc`, `/api/tenancy/resolve`
- Prefixes: `/api/platform/`, `/api/health/`, `/api/currency/`, `/api/payments/webhook/`
- Any path not starting with `/api`

### 3-Step Waterfall (`_resolve_tenant()`)

**Step 1: X-Tenant-ID header**
```
Header: X-Tenant-ID: acme
→ lookup Tenant by slug "acme" where is_active=true
```

**Step 2: Subdomain extraction**
```
Host: acme.rentmanager.com
→ extract "acme" from host parts
→ lookup Tenant by slug "acme"

Host: 192.168.1.100 (IP address)
→ regex detects IP → returns None → skips this step
```

**Step 3: Custom domain lookup**
```
Host: rentals.acme.com
→ query tenant_domains table for domain="rentals.acme.com"
→ join to tenants table where is_active=true
```

If all 3 fail → `400 {"detail": "Tenant not found. Provide X-Tenant-ID header."}`

### After Resolution
- `TenantContext(tenant, schema_name)` set on ContextVar
- All DB sessions auto-set `SET search_path TO <schema_name>, public`
- JWT tokens validated against tenant_id (token's `tenant_id` must match context)
- Context cleared after response

## Frontend Resolution

### Next.js Middleware (`frontend/src/middleware.ts`)

**Localhost/Dev:**
- URL pattern: `/t/<slug>/dashboard` → rewrite to `/dashboard`, set `x-tenant-slug` header
- This lets developers test multiple tenants without DNS setup

**Production:**
- Extract subdomain from host: `acme.example.com` → slug = `acme`
- Set `x-tenant-slug` header on response

### TenantInitializer Component (`frontend/src/components/tenant-initializer.tsx`)

Runs client-side on mount:
1. Call `GET /api/tenancy/resolve?domain=<hostname>` — resolves custom domains
2. If on localhost, fall back to `/t/<slug>` URL extraction
3. Store slug in Zustand tenant-store + localStorage for persistence

### API Layer (`frontend/src/lib/api.ts`)

Axios request interceptor on every call:
```typescript
config.headers["X-Tenant-ID"] = slug;  // from tenant-store
config.headers.Authorization = `Bearer ${accessToken}`;  // from auth-store
```

## IP Address Behavior

When accessing via IP (e.g., `http://192.168.29.245:8000/api/...`):
1. X-Tenant-ID header → works if provided
2. Subdomain → **skipped** (IP regex match at middleware.py:64)
3. Custom domain → looks up `192.168.29.245` in tenant_domains → almost certainly no match
4. **Result: 400 error unless X-Tenant-ID header is sent**

Frontend handles this: axios interceptor always sends X-Tenant-ID from store.
For direct API calls (curl, Postman), must include `X-Tenant-ID: <slug>` header.

## Database Tables Involved

**Public schema:**
- `tenants` — id, name, slug (unique), schema_name, is_active, config JSONB
- `tenant_domains` — id, tenant_id (FK), domain (unique), is_primary, is_verified
