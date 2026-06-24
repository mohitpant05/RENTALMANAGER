# Data Model

## Multi-Tenant Schema Isolation

PostgreSQL schema-per-tenant. Each tenant gets own schema with isolated tables.

### Public Schema (shared)

| Table | Purpose |
|-------|---------|
| `tenants` | Tenant registry (slug, schema_name, config, currency, timezone) |
| `tenant_domains` | Custom domain → tenant mapping |
| `platform_config` | Platform-wide key/value settings |
| `platform_users` | Superadmin users (separate from tenant users) |

### Tenant Schema (per-tenant, e.g., `tenant_abc123`)

**Auth & RBAC:**
| Table | Purpose |
|-------|---------|
| `users` | Tenant users (email, password_hash, user_type, preferred_currency) |
| `roles` | Role definitions (admin, owner, renter, staff) |
| `permissions` | Permission codenames (`resource:own:create`, `booking:*:read`) |
| `role_permissions` | Role ↔ Permission mapping |
| `user_roles` | User ↔ Role assignment |

**Resources:**
| Table | Purpose |
|-------|---------|
| `resource_types` | Categorization with JSON attribute schema |
| `resources` | Individual resources with attributes JSONB, optional slot_config JSONB |
| (availability tables) | Per availability strategy (date_range, hourly, time_slot) |
| (pricing tables) | Per pricing provider |

**Bookings:**
| Table | Purpose |
|-------|---------|
| `bookings` | Booking records with state machine (pending→confirmed→active→completed/cancelled), timezone stored per booking |
| `booking_holds` | Temporary holds with expiry |

**Reviews:**
| Table | Purpose |
|-------|---------|
| `reviews` | Two-way reviews (guest→resource, owner→guest) |
| `review_ratings` | Category-level ratings |

**Other:**
| Table | Purpose |
|-------|---------|
| `notifications` | In-app notifications (event type, payload JSONB, read state) |
| `attachments` | File metadata (MinIO reference, ownership) |
| `payments` | Payment records linked to bookings |
| `payouts` | Owner payout tracking |

## Schema Provisioning

When new tenant created (`core/tenancy/provisioning.py`):
1. `CREATE SCHEMA IF NOT EXISTS tenant_<uuid_underscored>`
2. Create all tables from `TENANT_TABLE_REGISTRY` (union of all module table sets)
3. Seed default roles (admin, owner, renter)
4. Reset search_path to public

## Migrations

- Public schema: Alembic (`backend/alembic/versions/`)
- Tenant schemas: `provisioning.py` creates tables with `checkfirst=True`
- Current migrations: 0001 (public schema) through 0012 (slot_config on resources)
- Backend init container runs `alembic upgrade head` on k8s deploy

## Permission Format

Pattern: `domain:qualifier:action`

Examples: `resource:own:create`, `booking:any:read`, `review:own:update`

Wildcards: `resource:*:read` (any qualifier), `booking:own:*` (any action), `*:*:*` (full access)

Admin user_type bypasses all permission checks.
