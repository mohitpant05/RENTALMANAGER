# Backend — FastAPI Application

## Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, middleware stack, health endpoints
│   ├── config.py            # Pydantic Settings (env-driven)
│   ├── database.py          # Async SQLAlchemy engine, tenant-aware sessions
│   ├── celery_app.py        # Celery config (Redis broker)
│   ├── redis_client.py      # Redis connection
│   ├── rate_limiter.py      # SlowAPI rate limiter
│   ├── seed.py              # DB seeding entrypoint
│   │
│   ├── core/                # Platform-level modules
│   │   ├── tenancy/         # Tenant models, middleware, context, provisioning
│   │   ├── auth/            # User model, JWT, RBAC, invite system, password
│   │   ├── admin/           # Tenant admin (themes, config, domains, staff)
│   │   ├── search/          # Meilisearch client, indexing, sync, query
│   │   ├── storage/         # MinIO client, attachment model, presigned URLs
│   │   ├── notifications/   # In-app notification events, models, service
│   │   ├── email/           # Email providers (console, Gmail, Mandrill)
│   │   ├── payments/        # Payment models, Stripe/Razorpay/Manual providers
│   │   ├── payouts/         # Owner payout tracking
│   │   ├── commission/      # Platform commission config + calculation
│   │   ├── currency/        # Multi-currency exchange rates
│   │   └── common/          # Shared base models
│   │
│   └── domains/             # Business domain modules
│       ├── resources/       # Generic resource engine (types, attributes, pricing, availability)
│       ├── bookings/        # Booking engine (state machine, holds, locks)
│       └── reviews/         # Two-way reviews, ratings, moderation
│
├── alembic/                 # DB migrations
│   └── versions/            # 0001_public_schema through 0006_user_preferred_currency
│
├── scripts/                 # seed_dev.py, seed_demo.py, create_test_user.py
├── tests/                   # Unit + integration tests per module
└── Dockerfile               # Multi-stage (dev/prod targets)
```

## Key Modules

### Tenancy (`core/tenancy/`)
- `models.py` — `Tenant` (slug, schema_name, config JSONB), `TenantDomain`, `PlatformConfig`
- `middleware.py` — Resolves tenant from X-Tenant-ID header → subdomain → custom domain
- `context.py` — `ContextVar`-based `TenantContext` (tenant + schema_name), `get_current_tenant()`
- `provisioning.py` — Creates schema, tables, seeds default roles per tenant

### Auth (`core/auth/`)
- `models.py` — `User`, `Role`, `Permission`, `RolePermission`, `UserRole`, `PlatformUser`
- `jwt.py` — HS256 JWT (access 15min, refresh 7 days), token contains `tenant_id`
- `dependencies.py` — `get_current_user()`, `require_permission()`, wildcard permission matching
- `invite.py` — Staff invite system (token-based email invites)
- `service.py` — Register, login, refresh, user CRUD
- `password.py` — Password hashing (bcrypt)
- RBAC: `domain:qualifier:action` pattern, wildcard `*` support, admin bypasses all checks

### Resources (`domains/resources/`)
- Generic resource engine — tenant defines `ResourceType` with JSON schema
- Strategy pattern: availability (date_range, hourly, time_slot), pricing (providers)
- `templates.py` — Pre-built resource type templates
- `discovery.py` — Resource discovery/filtering

### Bookings (`domains/bookings/`)
- State machine: `pending → confirmed → active → completed/cancelled`
- Hold system with expiry, advisory locks for mutations
- `tasks.py` — Celery tasks for hold expiry

### Payments (`core/payments/`)
- Provider interface: Stripe, Razorpay, Manual
- Payment model links to bookings
- Webhook endpoint for payment provider callbacks

## Database

- PostgreSQL 17, async via `asyncpg`
- `SQLModel` ORM (SQLAlchemy + Pydantic)
- Connection pool: 20 + 10 overflow
- Tenant session sets `SET search_path TO <schema>, public`
- Alembic for public schema migrations; tenant tables created via `provisioning.py`

## Configuration

All via env vars (`app/config.py` → Pydantic `BaseSettings`):
- `DATABASE_URL` / `DATABASE_URL_SYNC`
- `REDIS_URL`, `MEILI_URL`, `MEILI_MASTER_KEY`
- `MINIO_ENDPOINT`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`
- `SECRET_KEY` (JWT signing)
- `SUPERADMIN_SECRET_KEY`, `ALLOWED_SUPERADMIN_IPS`
- `EMAIL_PROVIDER` (console/gmail/mandrill)
- `REGISTER_RATE_LIMIT` (default 30/min)
