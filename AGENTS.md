<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **RENTALMANAGER** (3408 symbols, 4636 relationships, 13 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/RENTALMANAGER/context` | Codebase overview, check index freshness |
| `gitnexus://repo/RENTALMANAGER/clusters` | All functional areas |
| `gitnexus://repo/RENTALMANAGER/processes` | All execution flows |
| `gitnexus://repo/RENTALMANAGER/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

# Project Structure

- `backend/` — FastAPI + SQLModel + Celery (Python 3.12, `uv` package manager)
- `frontend/` — Next.js 15 + React 19 + Tailwind CSS 4 (no test framework configured)

# Backend

## Setup
```bash
cd backend && uv pip install --system ".[dev]"
```

## Commands
| Task | Command |
|------|---------|
| Lint | `cd backend && ruff check .` |
| Test (all) | `cd backend && pytest --tb=short -q` |
| Test (single) | `cd backend && pytest tests/test_auth_unit.py -v` |
| Migrate | `docker compose exec backend alembic upgrade head` |
| New migration | `docker compose exec backend alembic revision --autogenerate -m "message"` |

## Testing Prerequisites
Integration tests need: postgres, redis, meilisearch, minio. CI runs them as services (see `.github/workflows/ci.yml`). Local: `make up` then `cd backend && pytest`.

## Notes
- `asyncio_mode = "auto"` in pytest config — no `@pytest.mark.asyncio` needed
- Multi-tenant: tenant resolution via `app/core/tenancy/middleware.py`
- Celery worker + beat run as separate deployments (see deploy.yml)
- Code in `app/` only (hatchling wheel target)

## Test Credentials

To create a test user for local development:

```bash
# Option 1: Using docker compose (recommended)
docker compose exec backend python -c "
import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from uuid import uuid4
import bcrypt
from app.core.auth.models import User

async def create():
    engine = create_async_engine('postgresql+asyncpg://rentmanager:rentmanager_dev@postgres:5432/rentmanager')
    async with AsyncSession(engine) as session:
        result = await session.exec(select(User).where(User.email == 'test@rentmanager.dev'))
        if result.first():
            print('User exists: test@rentmanager.dev / testpassword123')
            return
        user = User(
            id=uuid4(), email='test@rentmanager.dev',
            password_hash=bcrypt.hashpw('testpassword123'.encode(), bcrypt.gensalt()).decode(),
            full_name='Test User', is_active=True, is_verified=True, user_type='admin'
        )
        session.add(user)
        await session.commit()
        print('Created: test@rentmanager.dev / testpassword123')
    await engine.dispose()

asyncio.run(create())
"

# Option 2: Direct script (requires services running)
cd backend && python scripts/create_test_user.py
```

Login at: `http://localhost:3000/login`

**Current test credentials:**
- Email: `test@rentmanager.dev`
- Password: `testpassword123`
- Role: `admin` (full access)

# Frontend

## Commands
| Task | Command |
|------|---------|
| Dev | `cd frontend && npm run dev` (uses Turbopack) |
| Build | `cd frontend && npm run build` |
| Lint | `cd frontend && npm run lint` |

## Notes
- Import alias: `@/*` maps to `frontend/src/*` (tsconfig paths)
- Tailwind CSS v4 (not v3) with `@tailwindcss/postcss`
- shadcn v4 + `class-variance-authority` for component variants
- No test runner configured

# Docker & Deploy

- `make up` / `make down` — docker compose wrappers
- `make test` — runs pytest inside backend container
- Deploy: pushes to ECR, updates k3s via kubectl (see `.github/workflows/deploy.yml`)
- Two compose files: `docker-compose.yml` (dev), `docker-compose.prod.yml`

---

# Implementation Plan (OpenCode)

Work through phases sequentially. Each task has acceptance criteria — don't move on until met. Commit after each phase completes.

## Phase 1: Rework Uncommitted Changes & Clean Commit

Current branch `feat/auth-email-invite` has ~34 modified/new files. Four areas need rework before committing.

### 1.1 — Route Restructure

Old `(admin)/` route group was deleted, replaced by `/admin/` path segment. Public pages in `(public)/` group.

- [ ] Ensure `/admin/*` routes are auth-gated in `frontend/src/middleware.ts` — redirect to `/login` if no token or if user is not admin/staff
- [ ] Create `frontend/src/app/(public)/layout.tsx` with shared public header (nav with logo, sign-in/sign-up links, user menu when authenticated) and footer
- [ ] Verify root `page.tsx` (public homepage) renders without authentication
- [ ] Verify `frontend/src/app/admin/layout.tsx` includes shell (icon-rail, sub-nav) and admin auth check
- [ ] Delete leftover `(admin)/` references if any remain in imports or configs

**Done when:** `npm run build` succeeds. Unauthenticated user sees homepage. `/admin` redirects to `/login`. Authenticated admin reaches admin dashboard.

### 1.2 — API baseURL

Changed from hardcoded `http://localhost:8000/api` to relative `/api`. Breaks dev without proxy.

- [ ] Add `NEXT_PUBLIC_API_URL` env var to `frontend/src/lib/api.ts`, default `http://localhost:8000/api`
- [ ] Add Next.js rewrites in `next.config.ts` to proxy `/api/:path*` → `http://localhost:8000/api/:path*` in dev
- [ ] Update `.env.example` (or create one) with `NEXT_PUBLIC_API_URL`
- [ ] Ensure token refresh in `api.ts` interceptor uses same base URL

**Done when:** Frontend works in dev with `npm run dev` + backend on port 8000. No hardcoded localhost in source.

### 1.3 — Public Registration

`register_user` and `RegisterRequest` added to backend. Was previously removed (commit `69b58a8`). Needs safety measures.

- [ ] Add rate limiting to `POST /api/auth/register` — use `slowapi` library with Redis backend (5 requests/min per IP, keyed by `request.client.host`)
- [ ] Add email uniqueness check per tenant in `register_user` service (return 409 if exists)
- [ ] Add password strength validation in `RegisterRequest` schema (min 8 chars)
- [ ] Frontend `/register` page: add form validation (email format, password match, min length)
- [ ] Registration should create user with `user_type="customer"` and no admin roles

**Done when:** Registration works end-to-end. Duplicate email returns error. Weak password rejected. Rate limit triggers after 5 rapid attempts.

### 1.4 — Public Pages & Components

New public-facing pages in `(public)/` group. Need review and fixes.

- [ ] `(public)/resources/[id]/page.tsx` — verify resource detail loads, image carousel works, booking card renders
- [ ] `(public)/bookings/page.tsx` — verify customer bookings list filters work (upcoming/active/past/cancelled)
- [ ] `(public)/bookings/[id]/page.tsx` — verify booking detail page loads with timeline
- [ ] `(public)/profile/page.tsx` — verify profile form renders (backend endpoint added in Phase 3)
- [ ] `(public)/notifications/page.tsx` — verify notifications list renders
- [ ] Homepage (`page.tsx`) — verify search/filter, resource cards, image loading via `useAttachments`
- [ ] Review all hooks: `use-booking-flow.ts`, `use-reviews.ts`, `use-notifications.ts`, `use-search.ts`, `use-storage.ts` — ensure API paths match backend routes
- [ ] Fix any TypeScript errors in `frontend/src/types/api.ts` for new types (`RegisterRequest`, `BookingResponse` fields, etc.)

**Done when:** `npm run build` passes with zero errors. All public pages render (may show empty data without backend, but no crashes).

### Phase 1 Commit

After all 1.x tasks pass:
- Stage all modified + new frontend and backend files
- Do NOT stage `frontend/tsconfig.tsbuildinfo`
- Commit message: `feat: add public-facing pages, registration, and route restructure`

---

## Phase 2: Docker Dev Environment

`docker-compose.yml` has infra only (Postgres, Redis, Meilisearch, MinIO, Traefik). Need app containers.

### 2.1 — Backend Dockerfile

- [ ] Create `backend/Dockerfile` — Python 3.12 slim, copy `pyproject.toml` + source, install with `uv pip install`
- [ ] Dev target: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- [ ] Add to `docker-compose.yml` as `backend` service with volume mount `./backend:/app` for hot-reload
- [ ] Depends on: postgres, redis
- [ ] Healthcheck: `curl -f http://localhost:8000/api/health`

### 2.2 — Frontend Dockerfile

- [ ] Create `frontend/Dockerfile` — Node 22 alpine, copy `package.json` + `package-lock.json`, `npm ci`, copy source
- [ ] Dev target: `next dev --hostname 0.0.0.0`
- [ ] Add to `docker-compose.yml` as `frontend` service with volume mount `./frontend:/app` (exclude `node_modules`)
- [ ] Set `NEXT_PUBLIC_API_URL=http://backend:8000/api` in container env

### 2.3 — Traefik Routing Rules

Traefik already in compose. Add routing labels:

- [ ] Frontend: default route, `Host` match on `localhost` and `*.localhost`
- [ ] Backend: `PathPrefix(/api)` routes to backend:8000
- [ ] Remove port mappings for backend/frontend (Traefik handles ingress on port 80)

### 2.4 — Celery Worker

- [ ] Add `celery-worker` service using same backend image
- [ ] Command: `celery -A app.celery_app worker --loglevel=info`
- [ ] Depends on: redis, postgres, backend (for migrations)

### 2.5 — Init & Migrations

- [ ] Add entrypoint script to backend: run `alembic upgrade head` then start uvicorn
- [ ] Add `seed` service or make target: `python scripts/seed_dev.py` (one-shot, runs after migrations)
- [ ] Document in AGENTS.md: `docker compose up` → full dev stack

**Done when:** `docker compose up` starts everything. `http://localhost` shows frontend. `http://localhost/api/health/all` returns all services OK. Tenant subdomain routing works via `*.localhost`.

---

## Phase 3: Missing Backend Endpoints & Wiring

### 3.1 — Profile Update Endpoint

- [ ] Add `PATCH /api/auth/me` in `backend/app/core/auth/router.py`
- [ ] Accept: `full_name`, `phone`, `avatar_url` (all optional)
- [ ] Require authentication (current user only)
- [ ] Add `ProfileUpdateRequest` schema in `backend/app/core/auth/schemas.py`
- [ ] Add `update_profile` function in `backend/app/core/auth/service.py`

**Done when:** Authenticated user can update profile fields. Changes persist. Unauthenticated request returns 401.

### 3.2 — Customer-Scoped Booking Endpoints

Current booking router is admin-oriented. Customers need their own views.

- [ ] Add `GET /api/bookings/mine` — returns bookings where `user_id` = current authenticated user
- [ ] Add ownership check to `GET /api/bookings/{id}` — admin sees all, customer sees only own
- [ ] Ensure `POST /api/bookings/` (create booking) works for customers, auto-sets `user_id` from token
- [ ] Verify booking state machine transitions are correct for customer-initiated flows (hold → confirm → complete)

**Done when:** Customer can list own bookings, view booking detail, create new booking. Cannot see other users' bookings.

### 3.3 — Email Wiring

Email factory exists (`backend/app/core/email/`) with Gmail and Mandrill providers. Not called anywhere.

- [ ] Wire invite acceptance → send welcome/confirmation email via Celery task
- [ ] Wire booking confirmation → send confirmation email with booking details
- [ ] Wire booking status change (confirmed, cancelled) → send notification email
- [ ] Add email templates as simple HTML strings in `backend/app/core/email/templates.py`
- [ ] Add `EMAIL_PROVIDER` env var (default: `console` for dev — just print to stdout)

**Done when:** Booking creation triggers email task. Invite acceptance triggers email. Dev mode prints emails to console. No external email service required for dev.

### 3.4 — Notification Endpoints

Backend notification module exists but may need fixes.

- [ ] Verify `GET /api/notifications` returns user-scoped notifications (not all tenants' notifications)
- [ ] Add `PATCH /api/notifications/{id}/read` — mark single notification as read
- [ ] Add `POST /api/notifications/read-all` — mark all as read for current user
- [ ] Ensure notification events fire on: booking created, booking status changed, review received
- [ ] Frontend `use-notifications.ts` hook must match these endpoint paths

**Done when:** Notifications appear for booking/review events. User can mark read. List is scoped to current user.

---

## Out of Scope (Claude Code / Later)

These are NOT part of this plan. Do not work on them:

- CI/CD pipeline configuration
- Production deployment config
- Frontend test suite (Jest/Playwright)
- WebSocket real-time notifications
- CSRF protection
- CORS env-based config for production
- Search (Meilisearch) full integration
- Theming applied to public pages
