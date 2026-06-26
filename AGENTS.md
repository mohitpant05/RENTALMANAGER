<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **RENTALMANAGER** (6854 symbols, 10392 relationships, 134 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
| Seed addons | `docker compose exec backend python -m scripts.seed_addons` |

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

# Goal
- Build and maintain a multi-tenant rental management platform (RentManager).

## Constraints & Preferences
- All uploads go through the backend proxy — no direct browser-to-MinIO access.
- All image downloads also go through the backend proxy (`/api/storage/proxy/{bucket}/{file_path}`) — no direct browser-to-MinIO.
- Use relative `/api` baseURL in frontend — works via Next.js rewrites (dev) or Ingress (prod).
- JWT access tokens have 15 min TTL, refresh tokens 7 days.
- Python-jose decodes tokens and enforces `exp` claim.
- Addon discovery for venues (cooks, vehicles) shows on the public resource detail page when dates are selected in booking flow.

## Progress
### Done
- **Addon per-day scheduling** — Full end-to-end flow for selecting addons with per-day breakdowns:
  - Backend: `schedules` JSONB column on `Booking` model; `AddonSchedule` schema; schedule-based pricing (`base_price × len(schedules)`) for `fixed_per_slot`/`fixed_per_day` models; `max_daily_servings: 4` in cook template.
  - New `POST /resources/{id}/availability/check-schedules` endpoint for per-window availability validation.
  - Extended `discover_addons` response to include `availability_model`, `pricing_model`, `slot_config` per type group.
  - Frontend: `AddonSchedulePicker` component — day checkboxes for vehicles, per-day time slot inputs for cooks.
  - Rewritten `AddonDiscoveredSection` — dropdown selector when >3 addon types, resource toggle expands schedule picker, structured selection state.
  - Booking detail page: "Add Add-ons" card after booking confirmation, calls hold + add-addon per selection.
  - `useAddons` hook: `checkSchedules()` and `holdAndAddAddon()` helper.

- Request-scoped logging (`app/core/logging.py` with `RequestLogger`, `ContextVar` for correlation ID).
- Step-by-step AUTH STEP 1/6 → 6/6 logging to `get_current_user()`.
- Fixed logging not showing in container output.
- Fixed upload 422: backend endpoint changed from `Query()` to `Form()` for `entity_type`/`entity_id`.
- Fixed image display: null-safe filtering, `download_url`/`file_name` mapping.
- Backend proxy for image downloads (`GET /api/storage/proxy/{bucket}/{file_path:path}`).
- Image delete button on attachment thumbnails.
- Back button on public resource detail page.
- Auth persistence on browser reload (`AuthInitializer` in root `Providers`).
- Resource table → detail sheet on row click.
- Booking slot validation UX with client-side duration check.
- Addon discovery wiring into booking card.
- **Admin bookings search & filter** — Search bar (by booking ID, resource name, customer name) + status filter tabs (All/Pending/Confirmed/Active/Completed/Cancelled/Rejected).
  - Backend: `search` parameter added to `list_bookings` service (joins `User` and `Resource` for ILIKE search across `Booking.id`, `User.email`, `User.full_name`, `Resource.name`).
  - Frontend: Admin bookings page has search input with Enter/key press, clearable, plus pill-style status filter buttons; table shows Customer column from `/api/auth/user/{id}` fetch.
- **Admin booking slots page** — Daily agenda view of all booked/held time slots across resources.
  - Backend: `GET /api/resources/availability/slots?start_date=&end_date=&resource_type_id=` endpoint returns availability records with resource name and type.
  - Frontend: `/admin/booking-slots` page with date navigation (prev/next/today), resource type filter, table view grouped by resource showing time ranges, status (booked/held), booking link, and hold token.
  - Slots icon in admin icon rail.

### In Progress
- (none)

### Blocked
- (none)

## Key Recent Decisions
- Per-day addon schedules stored as JSONB on `Booking` — avoids separate table, simple metadata approach.
- Addon hold = single hold for overall booking period, schedules = metadata (not per-slot holds). Coarse overlap check during discovery, per-window check available via dedicated endpoint.
- Addon selection happens post-venue-confirmation on booking detail page (primary flow), with bundled option also available.
- Vehicles: per-day checkbox (no time slots). Cooks: per-day time slot pickers matching `duration_options`.
- More than 3 addon type groups → dropdown selector; ≤3 types → all shown expanded.

## Relevant Files

### Backend
| File | Purpose |
|------|---------|
| `app/domains/bookings/models.py` | `Booking` model with `schedules` JSONB column |
| `app/domains/bookings/schemas.py` | `AddonSchedule`, updated `BookingCreate`/`BookingItemCreate`/`AddAddonRequest`/`BookingResponse` |
| `app/domains/bookings/service.py` | `create_booking` persists schedules, schedule-based pricing override |
| `app/domains/bookings/router.py` | Passes schedules through bundled/add-addon routes |
| `app/domains/resources/schemas.py` | `ScheduleCheckItem`, `SchedulesCheckRequest`, `SchedulesCheckResponse` |
| `app/domains/resources/service.py` | `check_schedule_availability()` — per-window validation |
| `app/domains/resources/router.py` | `POST /{id}/availability/check-schedules` endpoint |
| `app/domains/resources/discovery.py` | Returns `availability_model`, `pricing_model`, `slot_config` in addon type groups |
| `app/domains/resources/templates.py` | Cook template with `max_daily_servings: 4` |

### Frontend
| File | Purpose |
|------|---------|
| `components/public/addon-schedule-picker.tsx` | Per-day schedule configuration (vehicle checkboxes, cook time slots) |
| `components/public/addon-discovered-section.tsx` | Full addon discovery UI with dropdown grouping, expandable schedule pickers |
| `hooks/use-addons.ts` | `checkSchedules()`, `holdAndAddAddon()` helpers |
| `types/api.ts` | All addon/schedule types |
| `app/(public)/bookings/[id]/page.tsx` | Post-booking "Add Add-ons" card |

## Addon Booking Flow
1. Customer books a venue (existing `BookingCard` flow)
2. Redirected to `/bookings/{id}`  
3. If venue resource type has `role="primary"`, "Add Add-ons" card appears
4. `AddonDiscoveredSection` fetches available addons for the booking dates
5. If >3 addon types, dropdown selector shown
6. Customer toggles desired addons → expands per-day schedule picker:
   - **Vehicles**: checkbox each day of stay (no time slots)
   - **Cooks**: per-day time inputs matching `duration_options`
7. "Add Selected Add-ons" creates a hold for each addon (full period) + calls `POST /bookings/{id}/add-addon` with schedules
8. Addon bookings created with same `booking_group_id`, linked via `parent_booking_id`

## API Endpoints (Addon-specific)
| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/resources/{id}/addons?start_date=&end_date=` | Discover available addons for a venue |
| `POST` | `/resources/{id}/availability/check-schedules` | Validate per-day/time slot windows |
| `POST` | `/bookings/{id}/add-addon` | Add an addon to an existing booking |
| `POST` | `/bookings/bundled` | Create venue + addons in one bundled booking |

## Next Steps
- Wire selected addon IDs from `AddonDiscoveredSection` into the bundled booking creation flow (pre-checkout).
- Show existing addon bookings (siblings via `booking_group_id`) on booking detail page.
- Build ResourceAssignment admin UI for linking addon resources to venues.
- Allow admins to set `role` and `discovery_radius_km` on ResourceType settings in admin panel.

## Critical Context
- **Access token TTL**: 15 minutes. **Refresh token TTL**: 7 days. Auth init runs on every page load via `AuthInitializer`.
- **Tenant resolution**: `X-Tenant-ID: demo` → `_get_tenant_by_slug("demo")` → public `tenants` table query.
- **Middleware order**: `SuperadminIPMiddleware` → `TenantMiddleware` → `CORSMiddleware` → `SlowAPIMiddleware` → Router.
- **MinIO admin**: user `minioadmin`, password `minioadmin_dev`, console `http://localhost:9001`.
- **Slot config format**: `{"duration_options": ["1h", "1.5h", "2h", "3h"], "max_daily_servings": 4}` — stored on `ResourceType.slot_config` as JSONB.
- **Addon discovery**: `GET /resources/{id}/addons?start_date=...&end_date=...` — returns assigned + nearby addons grouped by type, with availability per window.
- **Resource roles**: `primary` (venue that can have addons), `addon` (cook/vehicle linked to a venue), `standalone` (default), `hidden`.
- **ResourceAssignment**: links `addon_resource_id` to `primary_resource_id` with a `priority`. Addons must be assigned to a venue to appear in discovery. No admin UI yet — use seed script or API directly.
- **seed_demo.py**: Creates resource types from templates + demo resources + bookings + reviews. Does NOT set roles or create ResourceAssignments.
- **seed_addons.py**: Post-seed script that sets roles (venues→primary, cooks/vehicles→addon), creates ResourceAssignments linking all cooks/vehicles to all venues, and creates 30 days of availability. Run: `docker compose exec backend python -m scripts.seed_addons`.
