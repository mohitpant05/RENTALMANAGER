# RentManager — Multi-Tenant Rental Management Platform

A modular monolith for managing rentals — resources, bookings, payments, reviews, and notifications — with schema-per-tenant isolation.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS v4, shadcn/ui, Zustand |
| Backend | FastAPI (Python 3.12), SQLModel, Alembic, Celery |
| Database | PostgreSQL 17 (schema-per-tenant multitenancy) |
| Cache/Broker | Redis 7 (Celery broker + rate limiting + token storage) |
| Search | Meilisearch v1.12 (per-tenant indexes, geo search, faceted filters) |
| File Storage | MinIO (S3-compatible, per-tenant bucket isolation) |
| Reverse Proxy | Traefik v3 (dev), NGINX Ingress (k8s prod) |
| Container Runtime | Docker Compose (dev), k3s (prod) |
| CI/CD | GitHub Actions → AWS ECR → k3s rolling deploy |
| IaC | Terraform (AWS: EKS, RDS, ElastiCache, S3, ECR; Cloudflare DNS) |
| Email | Pluggable: Console (dev), Gmail SMTP, Mandrill API |

## Architecture

```
Internet
  │
  ├─ [Dev] Traefik :80
  │     /api/* → backend:8000
  │     /*     → frontend:3000
  │
  ├─ [Prod] NGINX Ingress
  │     /api/* → backend Service:8000
  │     /*     → frontend Service:3000
  │
  ▼
┌─────────────┐  ┌──────────────┐  ┌────────────────┐
│  Frontend   │  │   Backend    │  │  Celery Worker  │
│  Next.js    │──│  FastAPI     │──│  Background     │
│  :3000      │  │  :8000       │  │  tasks          │
└─────────────┘  └──────┬───────┘  └───────┬────────┘
                        │                  │
          ┌─────────────┼──────────────────┘
          ▼             ▼
    ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────┐
    │ Postgres │  │  Redis   │  │ Meilisearch  │  │  MinIO   │
    │  :5432   │  │  :6379   │  │   :7700      │  │ :9000    │
    └──────────┘  └──────────┘  └──────────────┘  └──────────┘
```

### Multi-Tenancy

Schema-per-tenant in PostgreSQL. Public schema holds `tenants`, `tenant_domains`, and `platform_config`. Each tenant gets an isolated schema (e.g., `tenant_abc123`) with its own `users`, `roles`, `resources`, `bookings`, `reviews`, `notifications`, `payments`, and `payouts`.

Tenant resolution waterfall: `X-Tenant-ID` header → subdomain → custom domain lookup.

### Request Flow

1. HTTP request hits Traefik (dev) / NGINX Ingress (prod)
2. Routed by path: `/api/*` → backend, `/*` → frontend
3. Backend middleware: `SuperadminIPMiddleware` → `TenantMiddleware` → `SlowAPIMiddleware` → `CORSMiddleware`
4. FastAPI router handles request with tenant context set via `ContextVar`
5. DB session auto-sets `search_path` to tenant's schema

## Features

- **Auth & RBAC** — JWT access/refresh tokens (15min/7day), bcrypt passwords, role-based permissions (`domain:qualifier:action` with wildcards), staff invite system
- **Resource Engine** — Admin-defined resource types with dynamic JSONB attributes, strategy-pattern availability (date_range/hourly/time_slot) and pricing (per_day/per_hour/per_slot/tiered)
- **Booking Engine** — State machine (`pending→confirmed→active→completed/cancelled`), hold system with advisory locks, cancellation policies with refund calculation, bundled bookings (primary + addons), Celery lifecycle transitions
- **Search & Discovery** — Meilisearch integration, geo-spatial search, faceted filters, per-tenant indexes, addon discovery via haversine
- **Reviews & Ratings** — Two-way reviews (guest→resource, owner→guest), category ratings, moderation workflow, Meilisearch rating sync
- **Payments** — Provider pattern (Manual/Stripe/Razorpay), payment state machine, refund flow, payout tracking for owners
- **Commission System** — Platform commission config per resource type (or per resource), breakdown calculation (owner payout, service fee, platform commission)
- **Notifications** — In-app notifications fired on booking/review events, Celery email dispatch
- **Admin Panel** — Tenant admin (themes, custom domains, staff management, resource type management)
- **Superadmin Platform** — IP-whitelisted platform panel for managing tenants, platform-wide settings, dashboard stats
- **File Storage** — MinIO presigned upload/download URLs, attachment model with entity scoping

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Make

### Local Development

```bash
# Start all services
docker compose up -d

# Run migrations
docker compose exec backend alembic upgrade head

# Create a test tenant and user (optional)
docker compose exec backend python scripts/seed_dev.py
```

The stack starts: postgres, redis, meilisearch, minio, traefik, backend, celery-worker, celery-beat, and frontend.

- `http://localhost` — Frontend (via Traefik)
- `http://localhost/api/health` — Backend health
- `http://localhost:8080` — Traefik dashboard
- `http://localhost:9001` — MinIO console

### Test Credentials

After seeding, login at `http://localhost:3000/login`:
- Email: `test@rentmanager.dev`
- Password: `testpassword123`
- Role: `admin` (full access)

### Common Commands

| Command | Description |
|---------|-------------|
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | Tail all logs |
| `make test` | Run pytest in backend container |
| `make migrate` | Run Alembic migrations |
| `make psql` | Open PostgreSQL shell |

### Backend (without Docker)

```bash
cd backend
uv pip install --system ".[dev]"
ruff check .
pytest --tb=short -q
```

### Frontend (without Docker)

```bash
cd frontend
npm run dev        # dev with Turbopack
npm run build      # production build
npm run lint       # ESLint
```

## Project Structure

```
RM/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app, middleware stack, health
│   │   ├── config.py                 # Pydantic Settings (env-driven)
│   │   ├── database.py               # Async engine, tenant-aware sessions
│   │   ├── celery_app.py             # Celery + beat schedule
│   │   ├── core/
│   │   │   ├── tenancy/              # Tenant models, middleware, provisioning
│   │   │   ├── auth/                 # User model, JWT, RBAC, invite, passwords
│   │   │   ├── admin/                # Tenant admin (themes, config, staff)
│   │   │   ├── search/               # Meilisearch client, indexing, sync
│   │   │   ├── storage/              # MinIO client, presigned URLs
│   │   │   ├── notifications/        # In-app notification events
│   │   │   ├── email/                # Console/Gmail/Mandrill providers
│   │   │   ├── payments/             # Stripe/Razorpay/Manual providers
│   │   │   ├── payouts/              # Owner payout tracking
│   │   │   ├── commission/           # Platform commission config + calc
│   │   │   └── currency/             # Exchange rates
│   │   └── domains/
│   │       ├── resources/            # Resource types, availability, pricing
│   │       ├── bookings/             # State machine, holds, bundled bookings
│   │       └── reviews/              # Two-way reviews, moderation
│   ├── alembic/                      # Migrations (0001–0006)
│   ├── scripts/                      # Seed utilities
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                      # App Router (public + admin routes)
│   │   ├── components/               # Shared UI components
│   │   ├── hooks/                    # use-auth, use-search, use-booking-flow, etc.
│   │   ├── lib/                      # API client, Zustand stores, utils
│   │   ├── types/                    # TypeScript type definitions
│   │   └── middleware.ts             # Edge middleware (tenant + auth routing)
│   └── Dockerfile
├── k8s/                              # k3s production manifests
├── traefik/                          # Dev Traefik config
├── knowledge/                        # System knowledge base (HLD + LLD docs)
└── refDocs/                          # Implementation plans
```

## API Overview

| Group | Key Endpoints |
|-------|---------------|
| Auth | `POST /api/auth/register`, `/login`, `/refresh`, `/logout`; `GET /api/auth/me`; `PATCH /api/auth/me` |
| Resources | `CRUD /api/resource-types`, `CRUD /api/resources`, `POST /api/resources/{id}/availability/{check,hold,release}` |
| Bookings | `POST /api/bookings` (with hold), `GET /api/bookings/mine`, state transitions (`confirm`, `reject`, `cancel`, `no-show`), bundled bookings |
| Payments | `POST /api/payments/booking/{id}`, mark-paid, refund |
| Search | `POST /api/search` (public, faceted, geo) |
| Reviews | `POST /api/reviews` (guest→resource, lister→guest), moderation |
| Notifications | `GET /api/notifications`, `POST /{id}/read`, `POST /read-all` |
| Storage | `POST /api/storage/upload` (multipart, proxied), `GET /attachments`, `DELETE /attachments/{id}` |
| Admin | `GET/PATCH /api/admin/tenant`, staff CRUD, domains, themes |
| Platform | `GET/POST /api/platform/tenants`, dashboard stats, settings |

All endpoints prefixed with `/api/`. Auth via `Authorization: Bearer <token>`. Tenant via `X-Tenant-ID: <slug>` header.

## Documentation

The `knowledge/` directory contains the system knowledge base:

### High-Level Design
- [`knowledge/architecture-overview.md`](knowledge/architecture-overview.md) — System architecture, service map, tech stack
- [`knowledge/backend.md`](knowledge/backend.md) — FastAPI modules, DB, multi-tenancy
- [`knowledge/frontend.md`](knowledge/frontend.md) — Next.js structure, state, API layer
- [`knowledge/deployment.md`](knowledge/deployment.md) — Docker Compose, CI/CD
- [`knowledge/kubernetes.md`](knowledge/kubernetes.md) — k3s manifests, ingress, network policies
- [`knowledge/tenant-resolution.md`](knowledge/tenant-resolution.md) — Tenant ID resolution end-to-end
- [`knowledge/data-model.md`](knowledge/data-model.md) — Database schema, isolation, migrations

### Low-Level Design
- `knowledge/lld-api-contracts.md` — All API request/response schemas
- `knowledge/lld-auth-flow.md` — JWT structure, auth sequences, RBAC matching
- `knowledge/lld-booking-state-machine.md` — State transitions, concurrency, cancellation
- `knowledge/lld-availability-system.md` — Availability providers, hold lifecycle
- `knowledge/lld-pricing-commission.md` — Pricing models, commission calculation
- `knowledge/lld-search-indexing.md` — Meilisearch index structure, sync strategy
- `knowledge/lld-payment-integration.md` — Payment provider pattern, refund flow
- `knowledge/lld-celery-tasks.md` — Background tasks, multi-tenant execution
- `knowledge/lld-payout-system.md` — Owner payout tracking, settle flow
- `knowledge/lld-reviews-ratings.md` — Two-way reviews, moderation, aggregation
- `knowledge/lld-storage-email-currency.md` — MinIO, email providers, currency

## Deployment

### CI

GitHub Actions (`.github/workflows/ci.yml`):
- Backend lint (`ruff check`) + test (pytest against real services)
- Frontend type check + lint

### CD

GitHub Actions (`.github/workflows/deploy.yml`):
1. CI runs
2. Docker build → push to AWS ECR (`<sha>` + `latest` tags)
3. `kubectl set image` rolling update on k3s cluster

### Production

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

k3s manifests in `k8s/` directory (namespace `rentmanager`).
