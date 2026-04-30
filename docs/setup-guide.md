# RentManager — Project Setup Guide

## Prerequisites

- Docker & Docker Compose v2
- Git
- Node.js 22+ (for local frontend dev without Docker)
- Python 3.12+ (for local backend dev without Docker)

## 1. Clone & Environment

```bash
git clone https://github.com/mohitpant05/RENTALMANAGER.git
cd RENTALMANAGER
```

No `.env` file required for dev — all defaults are baked into `docker-compose.yml` via `${VAR:-default}` syntax. Defaults:

| Variable | Default |
|----------|---------|
| `POSTGRES_USER` | `rentmanager` |
| `POSTGRES_PASSWORD` | `rentmanager_dev` |
| `POSTGRES_DB` | `rentmanager` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `MEILI_MASTER_KEY` | `masterkey_dev` |
| `SECRET_KEY` | `dev-secret-key-change-in-production` |

To override, create a `.env` file in the project root.

## 2. Start Everything

```bash
docker compose up --build -d
```

This starts **9 services**:

| Service | Port | Purpose |
|---------|------|---------|
| **postgres** | 5432 | PostgreSQL 17 — primary database |
| **redis** | 6379 | Redis 7 — sessions, cache, invite tokens, Celery broker |
| **meilisearch** | 7700 | Full-text search engine |
| **minio** | 9000 (API), 9001 (console) | S3-compatible file storage |
| **backend** | 8000 | FastAPI app (uvicorn with `--reload`) |
| **celery-worker** | — | Async task worker (email, booking lifecycle) |
| **celery-beat** | — | Periodic task scheduler |
| **frontend** | 3000 | Next.js 15 dev server |
| **traefik** | 80 (proxy), 8080 (dashboard) | Reverse proxy |

Wait for health checks:

```bash
docker compose ps
```

All services should show `healthy` or `running`.

## 3. Run Database Migrations

```bash
docker exec rm-backend alembic upgrade head
```

This runs all Alembic migrations. Multi-tenant migrations iterate `tenant_*` schemas automatically.

## 4. Seed a Tenant (First Time)

Use the platform API (no tenant context needed):

```bash
# Create a tenant
curl -X POST http://localhost:8000/api/platform/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "Demo Corp", "slug": "demo"}'
```

This creates a PostgreSQL schema `tenant_<uuid>` with all tenant tables.

## 5. Access the App

| URL | What |
|-----|------|
| `http://localhost:3000` | Frontend (Next.js) |
| `http://localhost:3000/t/demo/login` | Login for tenant "demo" (localhost routing) |
| `http://localhost:8000/api/docs` | Swagger UI |
| `http://localhost:8000/api/health` | Health check |
| `http://localhost:8080` | Traefik dashboard |
| `http://localhost:9001` | MinIO console (minioadmin/minioadmin_dev) |

## How the Pieces Connect

```
Browser
  │
  ├─ localhost:3000/* ──► Next.js (frontend container)
  │    │
  │    └─ /api/* rewrites ──► localhost:8000/api/* (backend container)
  │
  └─ via Traefik (port 80):
       ├─ /api/* ──► backend:8000
       └─ /* ──► frontend:3000
```

### Request flow: Browser → Backend

1. **Next.js rewrite** — `next.config.ts` rewrites `/api/*` to `http://localhost:8000/api/*`
2. **Axios interceptor** — `lib/api.ts` attaches `Authorization: Bearer <token>` and `X-Tenant-ID: <slug>` headers
3. **FastAPI receives** — Uvicorn hands request to the ASGI app
4. **TenantMiddleware** — resolves tenant from header/subdomain/domain, sets `ContextVar`
5. **Router + Dependencies** — `Depends(get_db)` opens a DB session with `SET search_path TO tenant_xxx`
6. **Response** — JSON back through the chain

### Traefik (production-like routing)

Traefik sits on port 80 and routes by path:
- `/api/*` → backend container (port 8000)
- `/*` → frontend container (port 3000, priority 1 = catch-all)

Config lives in `traefik/traefik.yml`. Routing rules are Docker labels in `docker-compose.yml`.

### Multi-tenancy in dev

On `localhost`, tenant is identified via URL path prefix `/t/{slug}/`:
- `http://localhost:3000/t/demo/login` — Next.js middleware extracts `demo`, sets `x-tenant-slug` header
- Frontend `TenantInitializer` component reads slug from URL, stores in Zustand + localStorage
- Axios interceptor sends `X-Tenant-ID: demo` on every API call

In production, tenant comes from subdomain: `demo.rentmanager.com`.

## Running Tests

```bash
# Backend tests (inside Docker — needs postgres + redis)
docker exec rm-backend pytest -v

# Specific test file
docker exec rm-backend pytest tests/test_invite_integration.py -v

# Frontend type check
docker exec rm-frontend npx tsc --noEmit
```

## Local Dev (Without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# Start postgres + redis locally or via Docker
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Needs `NEXT_PUBLIC_API_URL=http://localhost:8000` (or just runs with default proxy rewrite).

## Useful Commands

```bash
# Rebuild single service
docker compose up --build backend -d

# View logs
docker compose logs -f backend
docker compose logs -f celery-worker

# Shell into container
docker exec -it rm-backend bash
docker exec -it rm-frontend sh

# Reset database (destroys data)
docker compose down -v && docker compose up --build -d

# Run alembic migration
docker exec rm-backend alembic upgrade head

# Create new migration
docker exec rm-backend alembic revision --autogenerate -m "description"
```
