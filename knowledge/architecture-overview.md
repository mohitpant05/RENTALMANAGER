# Architecture Overview

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Zustand |
| Backend | FastAPI (Python 3.12), SQLModel, Alembic, Celery |
| Database | PostgreSQL 17 (schema-per-tenant multi-tenancy) |
| Cache/Broker | Redis 7 (Celery broker + rate limiting + caching) |
| Search | Meilisearch v1.12 (per-tenant indexes, geo search, faceted filters) |
| File Storage | MinIO (S3-compatible, per-tenant bucket isolation) |
| Reverse Proxy | Traefik v3.6 (dev), NGINX Ingress (k8s prod) |
| Container Runtime | Docker Compose (dev), k3s (prod) |
| CI/CD | GitHub Actions → AWS ECR → k3s rolling deploy |
| Email | Pluggable: Console (dev), Gmail SMTP, Mandrill |

## Service Map

```
Internet
  │
  ├─ [Dev] Traefik :80 ─────────────────────────┐
  │     /api/* → backend:8000                    │
  │     /*     → frontend:3000                   │
  │                                              │
  ├─ [Prod] NGINX Ingress ──────────────────────┐│
  │     /api/* → backend Service:8000           ││
  │     /*     → frontend Service:3000          ││
  │                                             ││
  ▼                                             ▼▼
┌─────────────┐  ┌──────────────┐  ┌────────────────┐
│  Frontend   │  │   Backend    │  │  Celery Worker  │
│  Next.js    │──│  FastAPI     │──│  Background     │
│  :3000      │  │  :8000       │  │  tasks          │
└─────────────┘  └──────┬───────┘  └───────┬────────┘
                        │                  │
          ┌─────────────┼──────────────────┤
          ▼             ▼                  ▼
    ┌──────────┐  ┌──────────┐  ┌──────────────┐
    │ Postgres │  │  Redis   │  │ Meilisearch  │
    │  :5432   │  │  :6379   │  │   :7700      │
    └──────────┘  └──────────┘  └──────────────┘
                                       │
                                ┌──────┴──────┐
                                │    MinIO    │
                                │  :9000/9001 │
                                └─────────────┘
```

## Request Flow

1. HTTP request hits reverse proxy (Traefik dev / NGINX Ingress prod)
2. Routed by path: `/api/*` → backend, `/*` → frontend
3. Backend middleware stack (order matters):
   - `SuperadminIPMiddleware` — IP whitelist for `/api/platform/*`
   - `TenantMiddleware` — resolves tenant from header/subdomain/domain
   - `SlowAPIMiddleware` — rate limiting
   - `CORSMiddleware` — CORS headers
4. FastAPI router handles request with tenant context set via ContextVar
5. DB session auto-sets `search_path` to tenant's schema

## Multi-Tenancy Model

- **Schema-per-tenant** isolation in PostgreSQL
- Public schema: `tenants`, `tenant_domains`, `platform_config`, `platform_users`
- Tenant schema (e.g., `tenant_abc123`): `users`, `roles`, `permissions`, `resources`, `bookings`, `reviews`, `notifications`, `attachments`, `payments`, `payouts`
- Tenant provisioning creates schema + tables + seeds default roles
