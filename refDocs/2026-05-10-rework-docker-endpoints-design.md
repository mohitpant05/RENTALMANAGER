# RentManager: Rework, Docker & Missing Endpoints

**Date:** 2026-05-10
**Branch:** `feat/auth-email-invite`
**Owner:** OpenCode (Phases 1-3), Claude Code (out-of-scope items)

## Context

Branch `feat/auth-email-invite` has ~34 uncommitted files spanning public registration, route restructure, public-facing pages, and API baseURL changes. Infrastructure docker-compose exists but lacks app containers. Several backend endpoints needed by frontend are missing.

## Phase 1: Rework Uncommitted Changes & Clean Commit

### 1.1 Route Restructure

Old `(admin)/` route group deleted, replaced by `/admin/` path segment. Public pages in `(public)/` group.

**Tasks:**
- Auth-gate `/admin/*` in Next.js middleware — redirect non-admin users to `/login`
- Create `(public)/layout.tsx` with shared header/footer
- Verify root `page.tsx` renders without auth
- Verify `admin/layout.tsx` includes admin shell + auth check

### 1.2 API baseURL

Hardcoded `localhost:8000` changed to relative `/api`. Needs env var + dev proxy.

**Tasks:**
- Add `NEXT_PUBLIC_API_URL` env var, default `http://localhost:8000/api`
- Add Next.js rewrites for `/api` proxy in dev
- Ensure refresh interceptor uses same base

### 1.3 Public Registration

Re-added after prior removal. Needs safety.

**Tasks:**
- Rate limiting via `slowapi` with Redis backend (5 req/min per IP, keyed by `request.client.host`)
- Email uniqueness check per tenant (409 on duplicate)
- Password strength validation (min 8 chars)
- Frontend form validation
- User type locked to `customer`

### 1.4 Public Pages & Components

**Tasks:**
- Review all `(public)/` pages compile and render
- Verify hooks match backend routes
- Fix TypeScript errors in `types/api.ts`

**Acceptance:** `npm run build` succeeds. Public pages render. Admin routes protected.

---

## Phase 2: Docker Dev Environment

### 2.1 Backend Container
- `backend/Dockerfile` — Python 3.12 slim, uvicorn with reload
- Volume mount for hot-reload, depends on postgres + redis

### 2.2 Frontend Container
- `frontend/Dockerfile` — Node 22 alpine, next dev
- Volume mount (exclude node_modules)

### 2.3 Traefik Routing
- `/api/*` → backend:8000
- Everything else → frontend:3000
- Tenant subdomain support via `*.localhost`

### 2.4 Celery Worker
- Same backend image, celery worker command
- Depends on redis + postgres

### 2.5 Init & Migrations
- Backend entrypoint: alembic upgrade head → uvicorn
- Seed script as one-shot service

**Acceptance:** `docker compose up` starts full stack. All health checks pass.

---

## Phase 3: Missing Backend Endpoints

### 3.1 Profile Update
- `PATCH /api/auth/me` — update full_name, phone, avatar_url
- Auth required, own profile only

### 3.2 Customer Booking Endpoints
- `GET /api/bookings/mine` — user-scoped bookings
- Ownership check on `GET /api/bookings/{id}`
- Customer can create bookings via `POST /api/bookings/`

### 3.3 Email Wiring
- Wire email factory to invite, booking confirmation, status changes
- Celery async tasks
- Console provider for dev (print to stdout)

### 3.4 Notification Endpoints
- User-scoped `GET /api/notifications`
- `PATCH /api/notifications/{id}/read`
- `POST /api/notifications/read-all`
- Fire on booking + review events

**Acceptance:** Profile saves. Customer sees own bookings. Emails print to console. Notifications work.

---

## Out of Scope

- CI/CD pipeline
- Production deployment
- Frontend tests (Jest/Playwright)
- WebSocket notifications
- CSRF protection
- CORS production config
- Meilisearch full integration
- Theming on public pages

---

## Key Files

| Area | Files |
|------|-------|
| Auth | `backend/app/core/auth/{router,service,schemas}.py` |
| Tenancy | `backend/app/core/tenancy/{middleware,router}.py` |
| Bookings | `backend/app/domains/bookings/{router,service}.py` |
| Notifications | `backend/app/core/notifications/{router,service,events}.py` |
| Email | `backend/app/core/email/{factory,gmail,mandrill,provider}.py` |
| Frontend API | `frontend/src/lib/api.ts` |
| Frontend Auth | `frontend/src/hooks/use-auth.ts`, `frontend/src/lib/auth-store.ts` |
| Frontend Routes | `frontend/src/app/(public)/`, `frontend/src/app/admin/` |
| Docker | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
