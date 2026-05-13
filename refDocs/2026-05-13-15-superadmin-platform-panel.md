# Superadmin Platform Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an always-available platform admin panel at `/superadmin/<secret_key>` with IP whitelist middleware, dashboard stats, platform settings CRUD, and a full tenant management UI.

**Architecture:** Backend adds IP whitelist middleware, dashboard stats endpoint, and platform settings CRUD to existing `/api/platform/` routes. Frontend adds a new `/superadmin/[secretKey]/` route tree with its own layout, auth context (separate from tenant auth), and pages for login, dashboard, tenant CRUD, theme editing, and settings. Secret key validated server-side in layout — invalid key → 404.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, slowapi | Next.js 15, React 19, TypeScript, Zustand, TanStack Query, Zod, shadcn/ui

---

## Pre-Implementation Notes

**What already exists (do NOT recreate):**
- `PlatformUser` model in `backend/app/core/auth/models.py`
- `create_platform_token`, `authenticate_platform_user`, `get_current_platform_user` in `backend/app/core/admin/platform_auth.py`
- Platform router with login, tenant CRUD, activate/deactivate in `backend/app/core/admin/platform_router.py`
- `PlatformLoginRequest`, `PlatformTokenResponse`, `TenantCreate`, `TenantResponse` schemas in `backend/app/core/admin/schemas.py`
- `TenantMiddleware` already exempts `/api/platform/` prefix in `backend/app/core/tenancy/middleware.py:16`
- `Settings` class in `backend/app/config.py`
- `limiter` (slowapi) in `backend/app/rate_limiter.py`
- shadcn/ui components: button, card, input, label, table, badge, sheet, sonner, select, dropdown-menu, separator, avatar, alert-dialog, textarea
- `api` axios instance in `frontend/src/lib/api.ts` with interceptors
- `useAuthStore` Zustand store in `frontend/src/lib/auth-store.ts`

**File Structure:**

```
backend/app/
├── config.py                              # ADD: superadmin_secret_key, allowed_superadmin_ips
├── core/
│   ├── admin/
│   │   ├── ip_middleware.py               # CREATE: IP whitelist middleware
│   │   ├── platform_router.py             # MODIFY: add dashboard stats, settings endpoints
│   │   └── schemas.py                     # MODIFY: add DashboardStats, PlatformSettingResponse
│   └── tenancy/
│       └── models.py                      # ADD: PlatformConfig already exists, reuse it
├── main.py                                # MODIFY: register IP middleware
backend/tests/
├── test_platform_unit.py                  # CREATE: unit tests
├── test_platform_integration.py           # CREATE: integration tests

frontend/src/
├── lib/
│   └── platform-store.ts                  # CREATE: Zustand store for platform auth
├── hooks/
│   └── use-platform.ts                    # CREATE: TanStack Query hooks for platform API
├── app/superadmin/
│   └── [secretKey]/
│       ├── layout.tsx                     # CREATE: validates secretKey, platform auth gate
│       ├── login/page.tsx                 # CREATE: platform login form
│       ├── dashboard/page.tsx             # CREATE: stats overview
│       ├── tenants/
│       │   ├── page.tsx                   # CREATE: tenant list
│       │   ├── new/page.tsx               # CREATE: create tenant form
│       │   └── [id]/
│       │       ├── page.tsx               # CREATE: tenant detail
│       │       └── theme/page.tsx         # CREATE: theme editor
│       └── settings/page.tsx              # CREATE: platform config
├── middleware.ts                           # MODIFY: pass through /superadmin/* routes
```

---

### Task 1: Add Config Settings for Superadmin

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add superadmin env vars to Settings**

In `backend/app/config.py`, add these fields to the `Settings` class after `debug: bool = True`:

```python
    superadmin_secret_key: str = "change-me-in-production-min-32-chars!!"
    allowed_superadmin_ips: str = ""
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/config.py
git commit -m "feat(platform): add superadmin secret key and IP whitelist config"
```

---

### Task 2: Create IP Whitelist Middleware

**Files:**
- Create: `backend/app/core/admin/ip_middleware.py`
- Create: `backend/tests/test_platform_unit.py`

- [ ] **Step 1: Write failing test for IP whitelist**

Create `backend/tests/test_platform_unit.py`:

```python
import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.testclient import TestClient

from app.core.admin.ip_middleware import SuperadminIPMiddleware


def _make_request(path: str, client_ip: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "root_path": "",
        "client": (client_ip, 0),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_ip_middleware_allows_when_whitelist_empty():
    async def call_next(request):
        return Response("ok", status_code=200)

    middleware = SuperadminIPMiddleware(app=None, allowed_ips="")
    request = _make_request("/api/platform/login", "1.2.3.4")
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ip_middleware_blocks_unlisted_ip():
    async def call_next(request):
        return Response("ok", status_code=200)

    middleware = SuperadminIPMiddleware(app=None, allowed_ips="10.0.0.1,10.0.0.2")
    request = _make_request("/api/platform/login", "1.2.3.4")
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ip_middleware_allows_listed_ip():
    async def call_next(request):
        return Response("ok", status_code=200)

    middleware = SuperadminIPMiddleware(app=None, allowed_ips="10.0.0.1,10.0.0.2")
    request = _make_request("/api/platform/login", "10.0.0.1")
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ip_middleware_skips_non_platform_paths():
    async def call_next(request):
        return Response("ok", status_code=200)

    middleware = SuperadminIPMiddleware(app=None, allowed_ips="10.0.0.1")
    request = _make_request("/api/auth/login", "1.2.3.4")
    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_platform_unit.py -v`
Expected: FAIL — `ImportError: cannot import name 'SuperadminIPMiddleware'`

- [ ] **Step 3: Implement IP whitelist middleware**

Create `backend/app/core/admin/ip_middleware.py`:

```python
import ipaddress

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

PLATFORM_PREFIXES = ("/api/platform/",)


class SuperadminIPMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allowed_ips: str = ""):
        super().__init__(app)
        self._networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for entry in allowed_ips.split(","):
            entry = entry.strip()
            if entry:
                self._networks.append(ipaddress.ip_network(entry, strict=False))

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not any(path.startswith(p) for p in PLATFORM_PREFIXES):
            return await call_next(request)

        if not self._networks:
            return await call_next(request)

        client_ip = request.client.host if request.client else "0.0.0.0"
        addr = ipaddress.ip_address(client_ip)
        if any(addr in net for net in self._networks):
            return await call_next(request)

        return Response(status_code=404)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_platform_unit.py -v`
Expected: 4 PASS

- [ ] **Step 5: Register middleware in main.py**

In `backend/app/main.py`, add import after existing imports:

```python
from app.core.admin.ip_middleware import SuperadminIPMiddleware
```

Add middleware registration after `app.add_middleware(TenantMiddleware)` (line 94):

```python
app.add_middleware(
    SuperadminIPMiddleware,
    allowed_ips=settings.allowed_superadmin_ips,
)
```

- [ ] **Step 6: Add rate limiting to platform login**

In `backend/app/core/admin/platform_router.py`, add import:

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from app.rate_limiter import limiter
```

Add rate limit decorator to `platform_login` function (before `async def`):

```python
@router.post("/login", response_model=PlatformTokenResponse)
@limiter.limit("5/15minutes")
async def platform_login(
    request: Request,
    data: PlatformLoginRequest,
    session: AsyncSession = Depends(get_session),
):
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/admin/ip_middleware.py backend/tests/test_platform_unit.py backend/app/main.py backend/app/core/admin/platform_router.py
git commit -m "feat(platform): add IP whitelist middleware and login rate limiting"
```

---

### Task 3: Add Dashboard Stats Endpoint

**Files:**
- Modify: `backend/app/core/admin/schemas.py`
- Modify: `backend/app/core/admin/platform_router.py`
- Modify: `backend/tests/test_platform_unit.py`

- [ ] **Step 1: Add DashboardStats schema**

In `backend/app/core/admin/schemas.py`, add at the end:

```python
class DashboardStatsResponse(BaseModel):
    total_tenants: int
    active_tenants: int
    inactive_tenants: int
    total_users: int
    total_bookings: int
    services: dict
```

- [ ] **Step 2: Write failing integration test**

Create `backend/tests/test_platform_integration.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.admin.platform_auth import create_platform_token
from app.core.auth.models import PlatformUser
from app.core.auth.password import hash_password
from app.main import app


@pytest.fixture
async def platform_token(db_session):
    user = PlatformUser(
        email="superadmin@test.com",
        password_hash=hash_password("superpass123"),
        full_name="Super Admin",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return create_platform_token(str(user.id))


@pytest.fixture
async def platform_client(db_engine):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_dashboard_stats(platform_client, platform_token, test_tenant):
    resp = await platform_client.get(
        "/api/platform/dashboard/stats",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_tenants" in data
    assert "active_tenants" in data
    assert data["total_tenants"] >= 1


@pytest.mark.asyncio
async def test_dashboard_stats_unauthenticated(platform_client):
    resp = await platform_client.get("/api/platform/dashboard/stats")
    assert resp.status_code == 403
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_platform_integration.py -v`
Expected: FAIL — 404

- [ ] **Step 4: Implement dashboard stats endpoint**

In `backend/app/core/admin/platform_router.py`, add imports:

```python
from sqlalchemy import func, text

from app.core.admin.schemas import (
    DashboardStatsResponse,
    PlatformLoginRequest,
    PlatformTokenResponse,
    TenantCreate,
    TenantResponse,
)
from app.core.tenancy.context import validate_schema_name
```

Add endpoint after the existing `platform_login`:

```python
@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def dashboard_stats(
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(Tenant))
    tenants = list(result.all())

    active = sum(1 for t in tenants if t.is_active)
    total_users = 0
    total_bookings = 0

    for tenant in tenants:
        if not tenant.is_active:
            continue
        try:
            validate_schema_name(tenant.schema_name)
            row = await session.execute(
                text(f"SELECT COUNT(*) FROM {tenant.schema_name}.users")
            )
            total_users += row.scalar() or 0
            row = await session.execute(
                text(f"SELECT COUNT(*) FROM {tenant.schema_name}.bookings")
            )
            total_bookings += row.scalar() or 0
        except Exception:
            continue

    from app.main import (
        _ping_meilisearch,
        _ping_minio,
        _ping_postgres,
        _ping_redis,
    )

    services = {
        "postgres": await _ping_postgres(),
        "redis": await _ping_redis(),
        "meilisearch": await _ping_meilisearch(),
        "minio": await _ping_minio(),
    }

    return DashboardStatsResponse(
        total_tenants=len(tenants),
        active_tenants=active,
        inactive_tenants=len(tenants) - active,
        total_users=total_users,
        total_bookings=total_bookings,
        services=services,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_platform_integration.py -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/admin/schemas.py backend/app/core/admin/platform_router.py backend/tests/test_platform_integration.py
git commit -m "feat(platform): add dashboard stats endpoint"
```

---

### Task 4: Add Platform Settings Endpoints

**Files:**
- Modify: `backend/app/core/admin/schemas.py`
- Modify: `backend/app/core/admin/platform_router.py`
- Modify: `backend/tests/test_platform_integration.py`

- [ ] **Step 1: Add settings schemas**

In `backend/app/core/admin/schemas.py`, add:

```python
class PlatformSettingResponse(BaseModel):
    id: uuid.UUID
    key: str
    value: str
    description: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlatformSettingUpdate(BaseModel):
    value: str
    description: str | None = None
```

- [ ] **Step 2: Write failing test**

Add to `backend/tests/test_platform_integration.py`:

```python
@pytest.mark.asyncio
async def test_platform_settings_crud(platform_client, platform_token):
    resp = await platform_client.get(
        "/api/platform/settings",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = await platform_client.put(
        "/api/platform/settings/test_key",
        json={"value": "test_value", "description": "A test setting"},
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["key"] == "test_key"
    assert resp.json()["value"] == "test_value"

    resp = await platform_client.get(
        "/api/platform/settings",
        headers={"Authorization": f"Bearer {platform_token}"},
    )
    assert len(resp.json()) == 1
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_platform_integration.py::test_platform_settings_crud -v`
Expected: FAIL — 404 or 405

- [ ] **Step 4: Implement settings endpoints**

In `backend/app/core/admin/platform_router.py`, add imports:

```python
from app.core.admin.schemas import (
    DashboardStatsResponse,
    PlatformLoginRequest,
    PlatformSettingResponse,
    PlatformSettingUpdate,
    PlatformTokenResponse,
    TenantCreate,
    TenantResponse,
)
from app.core.tenancy.models import PlatformConfig, Tenant
```

Add endpoints:

```python
@router.get("/settings", response_model=list[PlatformSettingResponse])
async def list_settings(
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(select(PlatformConfig))
    return list(result.all())


@router.put("/settings/{key}", response_model=PlatformSettingResponse)
async def upsert_setting(
    key: str,
    data: PlatformSettingUpdate,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(PlatformConfig).where(PlatformConfig.key == key)
    )
    setting = result.first()
    if setting is None:
        setting = PlatformConfig(key=key, value=data.value, description=data.description)
        session.add(setting)
    else:
        setting.value = data.value
        if data.description is not None:
            setting.description = data.description
        setting.updated_at = datetime.now(UTC)
        session.add(setting)
    await session.commit()
    await session.refresh(setting)
    return setting
```

Add missing import at top:

```python
from datetime import UTC, datetime
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_platform_integration.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/admin/schemas.py backend/app/core/admin/platform_router.py backend/tests/test_platform_integration.py
git commit -m "feat(platform): add settings GET/PUT endpoints"
```

---

### Task 5: Validate Secret Key Endpoint

**Files:**
- Modify: `backend/app/core/admin/platform_router.py`
- Modify: `backend/tests/test_platform_integration.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_platform_integration.py`:

```python
@pytest.mark.asyncio
async def test_validate_secret_key_correct(platform_client):
    from app.config import get_settings
    key = get_settings().superadmin_secret_key
    resp = await platform_client.post(
        "/api/platform/validate-key",
        json={"key": key},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


@pytest.mark.asyncio
async def test_validate_secret_key_wrong(platform_client):
    resp = await platform_client.post(
        "/api/platform/validate-key",
        json={"key": "wrong-key"},
    )
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_platform_integration.py::test_validate_secret_key_correct -v`
Expected: FAIL — 404

- [ ] **Step 3: Implement validate-key endpoint**

In `backend/app/core/admin/platform_router.py`, add:

```python
from app.config import get_settings as _get_settings


class ValidateKeyRequest(BaseModel):
    key: str


@router.post("/validate-key")
async def validate_secret_key(data: ValidateKeyRequest):
    settings = _get_settings()
    if data.key != settings.superadmin_secret_key:
        raise HTTPException(status_code=404, detail="Not found")
    return {"valid": True}
```

Add `BaseModel` import if missing — it's already imported via schemas. Add the `ValidateKeyRequest` inline in the router or in schemas:

In `backend/app/core/admin/schemas.py`, add:

```python
class ValidateKeyRequest(BaseModel):
    key: str
```

Update the import in platform_router:

```python
from app.core.admin.schemas import (
    DashboardStatsResponse,
    PlatformLoginRequest,
    PlatformSettingResponse,
    PlatformSettingUpdate,
    PlatformTokenResponse,
    TenantCreate,
    TenantResponse,
    ValidateKeyRequest,
)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_platform_integration.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/admin/platform_router.py backend/app/core/admin/schemas.py backend/tests/test_platform_integration.py
git commit -m "feat(platform): add secret key validation endpoint"
```

---

### Task 6: Frontend — Platform Auth Store & API

**Files:**
- Create: `frontend/src/lib/platform-store.ts`
- Create: `frontend/src/hooks/use-platform.ts`

- [ ] **Step 1: Create platform auth store**

Create `frontend/src/lib/platform-store.ts`:

```typescript
import { create } from "zustand";

const PLATFORM_TOKEN_KEY = "rm_platform_token";

interface PlatformAuthState {
  token: string | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  clearToken: () => void;
  loadToken: () => void;
}

export const usePlatformStore = create<PlatformAuthState>((set) => ({
  token: null,
  isAuthenticated: false,

  setToken: (token) => {
    localStorage.setItem(PLATFORM_TOKEN_KEY, token);
    set({ token, isAuthenticated: true });
  },

  clearToken: () => {
    localStorage.removeItem(PLATFORM_TOKEN_KEY);
    set({ token: null, isAuthenticated: false });
  },

  loadToken: () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem(PLATFORM_TOKEN_KEY);
    if (token) {
      set({ token, isAuthenticated: true });
    }
  },
}));
```

- [ ] **Step 2: Create platform API hooks**

Create `frontend/src/hooks/use-platform.ts`:

```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { usePlatformStore } from "@/lib/platform-store";

function platformApi() {
  const token = usePlatformStore.getState().token;
  return axios.create({
    baseURL: "/api/platform",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

export interface TenantResponse {
  id: string;
  name: string;
  slug: string;
  schema_name: string;
  is_active: boolean;
  config: Record<string, unknown> | null;
  base_currency: string;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_tenants: number;
  active_tenants: number;
  inactive_tenants: number;
  total_users: number;
  total_bookings: number;
  services: Record<string, { status: string; detail?: string }>;
}

export interface PlatformSetting {
  id: string;
  key: string;
  value: string;
  description: string | null;
  updated_at: string;
}

export function usePlatformLogin() {
  const { setToken } = usePlatformStore();
  return useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      const res = await platformApi().post("/login", data);
      return res.data as { access_token: string };
    },
    onSuccess: (data) => {
      setToken(data.access_token);
    },
  });
}

export function useValidateKey() {
  return useMutation({
    mutationFn: async (key: string) => {
      const res = await axios.post("/api/platform/validate-key", { key });
      return res.data as { valid: boolean };
    },
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["platform", "dashboard"],
    queryFn: async () => {
      const res = await platformApi().get("/dashboard/stats");
      return res.data as DashboardStats;
    },
    refetchInterval: 60_000,
  });
}

export function useTenants() {
  return useQuery({
    queryKey: ["platform", "tenants"],
    queryFn: async () => {
      const res = await platformApi().get("/tenants");
      return res.data as TenantResponse[];
    },
  });
}

export function useTenant(id: string) {
  return useQuery({
    queryKey: ["platform", "tenants", id],
    queryFn: async () => {
      const res = await platformApi().get(`/tenants/${id}`);
      return res.data as TenantResponse;
    },
    enabled: !!id,
  });
}

export function useCreateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; slug: string; base_currency?: string; timezone?: string }) => {
      const res = await platformApi().post("/tenants", data);
      return res.data as TenantResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "tenants"] }),
  });
}

export function useToggleTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, activate }: { id: string; activate: boolean }) => {
      const action = activate ? "activate" : "deactivate";
      const res = await platformApi().post(`/tenants/${id}/${action}`);
      return res.data as TenantResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "tenants"] }),
  });
}

export function usePlatformSettings() {
  return useQuery({
    queryKey: ["platform", "settings"],
    queryFn: async () => {
      const res = await platformApi().get("/settings");
      return res.data as PlatformSetting[];
    },
  });
}

export function useUpsertSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, value, description }: { key: string; value: string; description?: string }) => {
      const res = await platformApi().put(`/settings/${key}`, { value, description });
      return res.data as PlatformSetting;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "settings"] }),
  });
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/platform-store.ts frontend/src/hooks/use-platform.ts
git commit -m "feat(platform): add platform auth store and API hooks"
```

---

### Task 7: Frontend — Update Middleware for Superadmin Routes

**Files:**
- Modify: `frontend/src/middleware.ts`

- [ ] **Step 1: Add superadmin route passthrough**

In `frontend/src/middleware.ts`, add `/superadmin` to the passthrough before admin gating. After the tenant slug processing block (line 35), add this check before admin gating:

Replace the auth gating section (starting from line 38 `const authCookie = ...`):

```typescript
  // Superadmin routes — no tenant required, no admin cookie check
  if (pathname.startsWith("/superadmin")) {
    return NextResponse.next();
  }

  // Auth gating for admin routes
  const authCookie = request.cookies.get("rm_auth")?.value;

  if (ADMIN_ONLY.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
    if (!authCookie) {
      const loginUrl = request.nextUrl.clone();
      loginUrl.pathname = "/login";
      return NextResponse.redirect(loginUrl);
    }
    if (authCookie !== "admin" && authCookie !== "staff") {
      const loginUrl = request.nextUrl.clone();
      loginUrl.pathname = "/login";
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/middleware.ts
git commit -m "feat(platform): pass superadmin routes through middleware"
```

---

### Task 8: Frontend — Superadmin Layout with Key Validation

**Files:**
- Create: `frontend/src/app/superadmin/[secretKey]/layout.tsx`
- Create: `frontend/src/app/superadmin/[secretKey]/login/page.tsx`

- [ ] **Step 1: Create layout with key validation and auth gate**

Create `frontend/src/app/superadmin/[secretKey]/layout.tsx`:

```typescript
"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, usePathname } from "next/navigation";
import { usePlatformStore } from "@/lib/platform-store";
import { useValidateKey } from "@/hooks/use-platform";

export default function SuperadminLayout({ children }: { children: React.ReactNode }) {
  const params = useParams<{ secretKey: string }>();
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, loadToken } = usePlatformStore();
  const validateKey = useValidateKey();
  const [keyValid, setKeyValid] = useState<boolean | null>(null);

  useEffect(() => {
    loadToken();
  }, [loadToken]);

  useEffect(() => {
    if (!params.secretKey) return;
    validateKey.mutate(params.secretKey, {
      onSuccess: () => setKeyValid(true),
      onError: () => setKeyValid(false),
    });
  }, [params.secretKey]);

  useEffect(() => {
    if (keyValid === false) {
      router.replace("/not-found");
    }
  }, [keyValid, router]);

  useEffect(() => {
    if (keyValid && !isAuthenticated && !pathname.endsWith("/login")) {
      router.replace(`/superadmin/${params.secretKey}/login`);
    }
  }, [keyValid, isAuthenticated, pathname, params.secretKey, router]);

  if (keyValid === null) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (keyValid === false) return null;

  return (
    <div className="min-h-screen bg-background">
      {isAuthenticated && !pathname.endsWith("/login") ? (
        <div className="flex h-screen">
          <SuperadminSidebar secretKey={params.secretKey} />
          <main className="flex-1 overflow-y-auto p-6">{children}</main>
        </div>
      ) : (
        children
      )}
    </div>
  );
}

function SuperadminSidebar({ secretKey }: { secretKey: string }) {
  const pathname = usePathname();
  const { clearToken } = usePlatformStore();
  const router = useRouter();
  const base = `/superadmin/${secretKey}`;

  const links = [
    { href: `${base}/dashboard`, label: "Dashboard" },
    { href: `${base}/tenants`, label: "Tenants" },
    { href: `${base}/settings`, label: "Settings" },
  ];

  return (
    <nav className="flex w-56 flex-col border-r bg-card p-4">
      <h2 className="mb-6 text-lg font-semibold">Platform Admin</h2>
      <div className="flex flex-1 flex-col gap-1">
        {links.map((link) => (
          <a
            key={link.href}
            href={link.href}
            className={`rounded-md px-3 py-2 text-sm transition-colors ${
              pathname.startsWith(link.href)
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50"
            }`}
          >
            {link.label}
          </a>
        ))}
      </div>
      <button
        onClick={() => {
          clearToken();
          router.replace(`/superadmin/${secretKey}/login`);
        }}
        className="mt-auto rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-destructive/10"
      >
        Logout
      </button>
    </nav>
  );
}
```

- [ ] **Step 2: Create login page**

Create `frontend/src/app/superadmin/[secretKey]/login/page.tsx`:

```typescript
"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { usePlatformLogin } from "@/hooks/use-platform";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PlatformLoginPage() {
  const params = useParams<{ secretKey: string }>();
  const router = useRouter();
  const login = usePlatformLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    login.mutate(
      { email, password },
      {
        onSuccess: () => router.replace(`/superadmin/${params.secretKey}/dashboard`),
        onError: () => setError("Invalid credentials"),
      }
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Platform Admin</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={login.isPending}>
              {login.isPending ? "Signing in..." : "Sign In"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/superadmin/
git commit -m "feat(platform): add superadmin layout with key validation and login page"
```

---

### Task 9: Frontend — Dashboard Page

**Files:**
- Create: `frontend/src/app/superadmin/[secretKey]/dashboard/page.tsx`

- [ ] **Step 1: Create dashboard page**

Create `frontend/src/app/superadmin/[secretKey]/dashboard/page.tsx`:

```typescript
"use client";

import { useDashboardStats } from "@/hooks/use-platform";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  const { data: stats, isLoading } = useDashboardStats();

  if (isLoading || !stats) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Tenants" value={stats.total_tenants} />
        <StatCard title="Active Tenants" value={stats.active_tenants} />
        <StatCard title="Total Users" value={stats.total_users} />
        <StatCard title="Total Bookings" value={stats.total_bookings} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Service Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            {Object.entries(stats.services).map(([name, svc]) => (
              <Badge
                key={name}
                variant={svc.status === "ok" ? "default" : "destructive"}
              >
                {name}: {svc.status}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/superadmin/\[secretKey\]/dashboard/
git commit -m "feat(platform): add dashboard page with stats and service health"
```

---

### Task 10: Frontend — Tenant List Page

**Files:**
- Create: `frontend/src/app/superadmin/[secretKey]/tenants/page.tsx`

- [ ] **Step 1: Create tenant list page**

Create `frontend/src/app/superadmin/[secretKey]/tenants/page.tsx`:

```typescript
"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTenants, useToggleTenant } from "@/hooks/use-platform";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function TenantsPage() {
  const params = useParams<{ secretKey: string }>();
  const router = useRouter();
  const { data: tenants, isLoading } = useTenants();
  const toggle = useToggleTenant();
  const [search, setSearch] = useState("");

  const filtered = tenants?.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.slug.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tenants</h1>
        <Button onClick={() => router.push(`/superadmin/${params.secretKey}/tenants/new`)}>
          Create Tenant
        </Button>
      </div>

      <Input
        placeholder="Search by name or slug..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />

      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Slug</TableHead>
              <TableHead>Currency</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered?.map((tenant) => (
              <TableRow
                key={tenant.id}
                className="cursor-pointer"
                onClick={() => router.push(`/superadmin/${params.secretKey}/tenants/${tenant.id}`)}
              >
                <TableCell className="font-medium">{tenant.name}</TableCell>
                <TableCell>{tenant.slug}</TableCell>
                <TableCell>{tenant.base_currency}</TableCell>
                <TableCell>
                  <Badge variant={tenant.is_active ? "default" : "destructive"}>
                    {tenant.is_active ? "Active" : "Inactive"}
                  </Badge>
                </TableCell>
                <TableCell>{new Date(tenant.created_at).toLocaleDateString()}</TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant={tenant.is_active ? "destructive" : "default"}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggle.mutate({ id: tenant.id, activate: !tenant.is_active });
                    }}
                    disabled={toggle.isPending}
                  >
                    {tenant.is_active ? "Deactivate" : "Activate"}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/superadmin/\[secretKey\]/tenants/page.tsx
git commit -m "feat(platform): add tenant list page with search and status toggle"
```

---

### Task 11: Frontend — Create Tenant Page

**Files:**
- Create: `frontend/src/app/superadmin/[secretKey]/tenants/new/page.tsx`

- [ ] **Step 1: Create tenant form page**

Create `frontend/src/app/superadmin/[secretKey]/tenants/new/page.tsx`:

```typescript
"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useCreateTenant } from "@/hooks/use-platform";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function CreateTenantPage() {
  const params = useParams<{ secretKey: string }>();
  const router = useRouter();
  const create = useCreateTenant();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [timezone, setTimezone] = useState("UTC");
  const [error, setError] = useState("");

  function handleNameChange(val: string) {
    setName(val);
    setSlug(val.toLowerCase().replace(/[^a-z0-9-]/g, "-").replace(/-+/g, "-"));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    create.mutate(
      { name, slug, base_currency: currency, timezone },
      {
        onSuccess: (tenant) =>
          router.push(`/superadmin/${params.secretKey}/tenants/${tenant.id}`),
        onError: (err: any) =>
          setError(err.response?.data?.detail || "Failed to create tenant"),
      }
    );
  }

  return (
    <div className="mx-auto max-w-lg">
      <Card>
        <CardHeader>
          <CardTitle>Create Tenant</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => handleNameChange(e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                required
                pattern="^[a-z0-9-]+$"
              />
              <p className="text-xs text-muted-foreground">
                Used in subdomain: {slug || "..."}.rentmanager.com
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor="currency">Currency</Label>
                <Input
                  id="currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                  maxLength={3}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label htmlFor="timezone">Timezone</Label>
                <Input
                  id="timezone"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                />
              </div>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Creating..." : "Create Tenant"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/superadmin/\[secretKey\]/tenants/new/
git commit -m "feat(platform): add create tenant page"
```

---

### Task 12: Frontend — Tenant Detail Page

**Files:**
- Create: `frontend/src/app/superadmin/[secretKey]/tenants/[id]/page.tsx`

- [ ] **Step 1: Create tenant detail page**

Create `frontend/src/app/superadmin/[secretKey]/tenants/[id]/page.tsx`:

```typescript
"use client";

import { useParams } from "next/navigation";
import { useTenant, useToggleTenant } from "@/hooks/use-platform";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function TenantDetailPage() {
  const params = useParams<{ secretKey: string; id: string }>();
  const { data: tenant, isLoading } = useTenant(params.id);
  const toggle = useToggleTenant();

  if (isLoading || !tenant) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{tenant.name}</h1>
          <p className="text-muted-foreground">{tenant.slug}.rentmanager.com</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={tenant.is_active ? "default" : "destructive"}>
            {tenant.is_active ? "Active" : "Inactive"}
          </Badge>
          <Button
            variant={tenant.is_active ? "destructive" : "default"}
            onClick={() => toggle.mutate({ id: tenant.id, activate: !tenant.is_active })}
            disabled={toggle.isPending}
          >
            {tenant.is_active ? "Deactivate" : "Activate"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Row label="Schema" value={tenant.schema_name} />
            <Row label="Currency" value={tenant.base_currency} />
            <Row label="Timezone" value={tenant.timezone} />
            <Row label="Created" value={new Date(tenant.created_at).toLocaleString()} />
            <Row label="Updated" value={new Date(tenant.updated_at).toLocaleString()} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Config (JSON)</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-48 overflow-auto rounded bg-muted p-3 text-xs">
              {JSON.stringify(tenant.config, null, 2) || "null"}
            </pre>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Quick Links</CardTitle>
        </CardHeader>
        <CardContent className="flex gap-3">
          <Button variant="outline" size="sm" asChild>
            <a href={`/superadmin/${params.secretKey}/tenants/${tenant.id}/theme`}>
              Edit Theme
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono">{value}</span>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/superadmin/\[secretKey\]/tenants/\[id\]/page.tsx
git commit -m "feat(platform): add tenant detail page"
```

---

### Task 13: Frontend — Tenant Theme Editor Page

**Files:**
- Create: `frontend/src/app/superadmin/[secretKey]/tenants/[id]/theme/page.tsx`

- [ ] **Step 1: Add theme hooks to use-platform.ts**

In `frontend/src/hooks/use-platform.ts`, add:

```typescript
export interface ThemeResponse {
  id: string;
  tenant_id: string;
  brand: Record<string, unknown>;
  colors: Record<string, string>;
  typography: Record<string, unknown>;
  components: Record<string, unknown>;
  features: Record<string, unknown>;
  updated_at: string;
}

export function useTenantTheme(tenantId: string) {
  return useQuery({
    queryKey: ["platform", "tenants", tenantId, "theme"],
    queryFn: async () => {
      const res = await platformApi().get(`/tenants/${tenantId}/theme`);
      return res.data as ThemeResponse;
    },
    enabled: !!tenantId,
  });
}
```

Note: The theme GET endpoint does not exist on the platform router yet. We need to add it.

- [ ] **Step 2: Add platform theme endpoint to backend**

In `backend/app/core/admin/platform_router.py`, add:

```python
from app.core.admin.models import TenantTheme
from app.core.admin.schemas import ThemeResponse, ThemeUpdate


@router.get("/tenants/{tenant_id}/theme", response_model=ThemeResponse)
async def get_tenant_theme(
    tenant_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(TenantTheme).where(TenantTheme.tenant_id == tenant_id)
    )
    theme = result.first()
    if theme is None:
        raise HTTPException(status_code=404, detail="Theme not found")
    return ThemeResponse.model_validate(theme)


@router.put("/tenants/{tenant_id}/theme", response_model=ThemeResponse)
async def update_tenant_theme(
    tenant_id: uuid.UUID,
    data: ThemeUpdate,
    session: AsyncSession = Depends(get_session),
    platform_user: PlatformUser = Depends(get_current_platform_user),
):
    result = await session.exec(
        select(TenantTheme).where(TenantTheme.tenant_id == tenant_id)
    )
    theme = result.first()
    if theme is None:
        theme = TenantTheme(tenant_id=tenant_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(theme, field, value)
    theme.updated_at = datetime.now(UTC)
    session.add(theme)
    await session.commit()
    await session.refresh(theme)
    return ThemeResponse.model_validate(theme)
```

- [ ] **Step 3: Create theme editor page**

Create `frontend/src/app/superadmin/[secretKey]/tenants/[id]/theme/page.tsx`:

```typescript
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTenantTheme } from "@/hooks/use-platform";
import { usePlatformStore } from "@/lib/platform-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import axios from "axios";

export default function ThemeEditorPage() {
  const params = useParams<{ secretKey: string; id: string }>();
  const { data: theme, isLoading, refetch } = useTenantTheme(params.id);
  const { token } = usePlatformStore();
  const [colors, setColors] = useState<Record<string, string>>({});
  const [brandName, setBrandName] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (theme) {
      setColors((theme.colors as Record<string, string>) || {});
      setBrandName((theme.brand as Record<string, string>)?.name || "");
    }
  }, [theme]);

  async function handleSave() {
    setSaving(true);
    try {
      await axios.put(
        `/api/platform/tenants/${params.id}/theme`,
        {
          brand: { ...theme?.brand, name: brandName },
          colors,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("Theme saved");
      refetch();
    } catch {
      toast.error("Failed to save theme");
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Theme Editor</h1>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save Theme"}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Brand</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-2">
            <Label>Brand Name</Label>
            <Input value={brandName} onChange={(e) => setBrandName(e.target.value)} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Colors</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {Object.entries(colors).map(([key, value]) => (
              <div key={key} className="flex flex-col gap-1">
                <Label className="text-xs">{key}</Label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={value}
                    onChange={(e) => setColors({ ...colors, [key]: e.target.value })}
                    className="h-8 w-8 cursor-pointer rounded border"
                  />
                  <Input
                    value={value}
                    onChange={(e) => setColors({ ...colors, [key]: e.target.value })}
                    className="h-8 font-mono text-xs"
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Raw JSON</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-64 overflow-auto rounded bg-muted p-3 text-xs">
            {JSON.stringify(theme, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/superadmin/\[secretKey\]/tenants/\[id\]/theme/ frontend/src/hooks/use-platform.ts backend/app/core/admin/platform_router.py
git commit -m "feat(platform): add tenant theme editor page and platform theme endpoints"
```

---

### Task 14: Frontend — Platform Settings Page

**Files:**
- Create: `frontend/src/app/superadmin/[secretKey]/settings/page.tsx`

- [ ] **Step 1: Create settings page**

Create `frontend/src/app/superadmin/[secretKey]/settings/page.tsx`:

```typescript
"use client";

import { useState } from "react";
import { usePlatformSettings, useUpsertSetting } from "@/hooks/use-platform";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";

export default function SettingsPage() {
  const { data: settings, isLoading } = usePlatformSettings();
  const upsert = useUpsertSetting();
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newDesc, setNewDesc] = useState("");

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim()) return;
    upsert.mutate(
      { key: newKey, value: newValue, description: newDesc || undefined },
      {
        onSuccess: () => {
          toast.success(`Setting "${newKey}" saved`);
          setNewKey("");
          setNewValue("");
          setNewDesc("");
        },
        onError: () => toast.error("Failed to save setting"),
      }
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Platform Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Add / Update Setting</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleAdd} className="flex items-end gap-3">
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Key</Label>
              <Input value={newKey} onChange={(e) => setNewKey(e.target.value)} className="w-40" />
            </div>
            <div className="flex flex-1 flex-col gap-1">
              <Label className="text-xs">Value</Label>
              <Input value={newValue} onChange={(e) => setNewValue(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Description</Label>
              <Input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} className="w-48" />
            </div>
            <Button type="submit" disabled={upsert.isPending}>
              Save
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Current Settings</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-16 items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Key</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {settings?.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-mono text-sm">{s.key}</TableCell>
                    <TableCell>{s.value}</TableCell>
                    <TableCell className="text-muted-foreground">{s.description || "—"}</TableCell>
                    <TableCell>{new Date(s.updated_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
                {settings?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground">
                      No settings configured
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/app/superadmin/\[secretKey\]/settings/
git commit -m "feat(platform): add platform settings page"
```

---

### Task 15: Smoke Test the Full Flow

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest tests/test_platform_unit.py tests/test_platform_integration.py -v`
Expected: ALL PASS

- [ ] **Step 2: Start dev servers and test in browser**

Run backend: `cd backend && uvicorn app.main:app --reload`
Run frontend: `cd frontend && npm run dev`

Test flow:
1. Visit `http://localhost:3000/superadmin/change-me-in-production-min-32-chars!!` — should show login
2. Visit `http://localhost:3000/superadmin/wrong-key` — should 404
3. Login with superadmin credentials → dashboard with stats
4. Navigate to Tenants → see tenant list
5. Create tenant → form works, redirects to detail
6. Toggle activate/deactivate
7. Settings → add/view settings

- [ ] **Step 3: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix(platform): address smoke test issues"
```
