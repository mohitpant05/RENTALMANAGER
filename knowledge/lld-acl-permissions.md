# ACL & Permission System

## Overview

Role-based access control (RBAC) with per-user permission overrides. Every protected endpoint uses permission checks instead of `user_type` comparisons.

## User Type Hierarchy

```
Admin (tenant owner — sees everything always)
  └── Staff (manages listers, owns resources, creates on-behalf bookings)
        └── Lister (owns resources, stripped-down dashboard, NO on-behalf bookings)
              └── Customer (books resources from listers or staff)
```

**`user_type` enum**: `admin` | `staff` | `lister` | `customer`

- `admin` — tenant owner, bypasses all permission checks (`*:*:*`)
- `staff` — manages listers, owns resources directly, creates on-behalf bookings
- `lister` — resource owner operating under a staff member; cannot create on-behalf bookings, cannot confirm/reject bookings
- `customer` — end user who books resources

### Who Creates Whom

| Creator | Creates | Mechanism |
|---------|---------|-----------|
| Admin | Staff | Existing staff invite flow |
| Staff | Lister | Lister invite flow (`POST /api/admin/listers`) |
| Self-register | Customer | Public register endpoint |

## Permission Format

`domain:qualifier:action` — e.g. `bookings:*:confirm`

## Permission Hierarchy (Supersets)

`bookings:*:manage` automatically grants:
- `bookings:*:confirm`
- `bookings:*:reject`
- `bookings:*:cancel`
- `bookings:*:no_show`
- `bookings:*:create_on_behalf`

Admin users have `*:*:*` which bypasses all checks.

## Permission Resolution Order

1. Check `UserPermissionOverride` for user+permission — if exists, use `granted` value (true=grant, false=revoke)
2. Else check role-based permissions via `RolePermission` join
3. Admin (`user_type == "admin"`) gets `{"*:*:*"}` and bypasses all checks

## Key Dependency

`get_current_user_with_perms()` in `backend/app/core/auth/dependencies.py` returns `tuple[User, set[str]]`. Used by booking router and any endpoint needing permission checks.

`matches_permission(required, granted)` checks exact match, wildcard candidates, AND superset hierarchy.

## All Permissions (33 total)

| Domain | Permissions |
|--------|------------|
| resources | read, create, manage, delete, assign_for_customer |
| bookings | read, create, manage, cancel, confirm, reject, no_show, create_on_behalf |
| reviews | read, create, moderate |
| staff | invite, manage |
| pricing | read, configure |
| theme | read, edit |
| analytics | read |
| settings | manage |
| resource_types | manage |
| customers | read, create, manage, deactivate |
| listers | invite, read, manage |

## Default Roles

| Role | Key Permissions |
|------|----------------|
| admin | `*:*:*` (all) |
| staff | resources (read/create/manage/delete), bookings (read/manage/confirm/reject/no_show/create_on_behalf), reviews (read/moderate), customers (read/manage), listers (invite/read/manage), pricing read, analytics read |
| lister | resources (read/create/manage), bookings read, reviews read, pricing read |
| customer | resources read, bookings (read/create), reviews (read/create) |

### Lister Role Restrictions

Lister does NOT have:
- `bookings:*:create_on_behalf` — cannot book on behalf of customers
- `bookings:*:confirm` / `reject` / `no_show` — cannot manage booking state
- `customers:*:*` — no customer management
- `listers:*:*` — cannot manage other listers
- `staff:*:*`, `settings:*:*`, `theme:*:*`, `analytics:*:*`

## Data Model

### UserPermissionOverride (composite PK: user_id + permission_id)
- `user_id` UUID FK→users
- `permission_id` UUID FK→permissions
- `granted` bool (true=grant beyond role, false=revoke from role)
- `created_at` datetime

### User (relevant fields for isolation)
- `manager_id` UUID FK→users.id (nullable) — set only when `user_type = 'lister'`; links a lister to their managing staff member
- `ON DELETE SET NULL` — if staff is deactivated, listers become unassigned (admin can reassign)
- Relationships: `listers` (back-populates from manager_id), `manager`

### ResourceType addition
- `staff_booking_auto_confirm` bool (default true) — controls whether staff-created bookings auto-confirm

## Tenant Isolation Config

### `staff_isolation_mode`

Stored in the tenant config JSONB field. Controls whether staff data is isolated or shared.

| Value | Behavior |
|-------|----------|
| `"shared"` (default) | All staff see all data across the tenant — current behavior preserved |
| `"isolated"` | Each staff member sees only their own resources + their listers' resources + derived bookings/customers/reviews |

Admin always sees everything regardless of `staff_isolation_mode`.

Default is `"shared"` — zero behavior change on deploy for existing tenants.

## Data Scoping

### `DataScope` Utility (`backend/app/core/auth/scoping.py`)

```python
@dataclass
class DataScope:
    scope_type: Literal["all", "staff", "lister", "customer"]
    user_id: UUID
    lister_ids: list[UUID]  # preloaded for staff in isolated mode

async def get_data_scope(session, user, tenant_config) -> DataScope:
    """Resolves current user's data scope based on user_type and isolation config."""
```

FastAPI dependency:
```python
def get_scoped_user():
    """Returns (User, set[str], DataScope)"""
```

### Scoping Rules by User Type (isolated mode)

| user_type | Sees |
|-----------|------|
| admin | Everything |
| staff | Own resources + own listers' resources + bookings/reviews/customers derived from those |
| lister | Only own resources + bookings on own resources + reviews on own resources |
| customer | Own bookings only |

### Isolation by Entity

| Entity | Isolation method |
|--------|-----------------|
| Listers | Direct: `user.manager_id` FK points to staff |
| Resources | Via owner: `resource.owner_id` → staff directly, OR `resource.owner_id` → lister → `lister.manager_id` → staff |
| Bookings | Via resource chain: `booking.resource_id` → resource → owner chain |
| Customers | Derived from booking history: has at least one booking on a resource in staff's scope |
| Reviews | Via resource chain: `review.resource_id` → resource → owner chain |

### Customer Special Cases

- **Customer list page + autocomplete search**: filtered by manager scope (derived from booking history)
- **Email lookup** (`/auth/users/lookup?email=`): NOT filtered — always returns customer if exists. Enables cross-scope on-behalf booking.
- Same customer can be visible to multiple staff members if they booked from different staff's listers.

### Scoping Query Patterns

#### Resources (isolated mode, staff user)

```sql
SELECT r.* FROM resources r
LEFT JOIN users lister ON r.owner_id = lister.id
WHERE r.owner_id = :staff_id
   OR (lister.manager_id = :staff_id AND lister.user_type = 'lister')
```

#### Bookings (isolated mode, staff user)

```sql
SELECT b.* FROM bookings b
JOIN resources r ON b.resource_id = r.id
LEFT JOIN users lister ON r.owner_id = lister.id
WHERE r.owner_id = :staff_id
   OR (lister.manager_id = :staff_id AND lister.user_type = 'lister')
```

#### Customers (isolated mode, staff user)

```sql
SELECT DISTINCT u.* FROM users u
JOIN bookings b ON b.user_id = u.id
JOIN resources r ON b.resource_id = r.id
LEFT JOIN users lister ON r.owner_id = lister.id
WHERE u.user_type = 'customer'
  AND (r.owner_id = :staff_id OR lister.manager_id = :staff_id)
```

## API Endpoints

### Booking Guards
| Endpoint | Permission |
|----------|-----------|
| POST /bookings | `bookings:*:manage` (for is_admin flag) |
| GET /bookings | `bookings:*:read` (see all vs own) |
| GET /bookings/{id} | `bookings:*:read` OR booking owner |
| POST /bookings/{id}/confirm | `bookings:*:confirm` |
| POST /bookings/{id}/reject | `bookings:*:reject` |
| POST /bookings/{id}/cancel | `bookings:*:cancel` OR booking owner |
| POST /bookings/{id}/no-show | `bookings:*:no_show` |
| POST /bookings/on-behalf | `bookings:*:create_on_behalf` |

### Admin Override Endpoints
| Method | Path | Guard |
|--------|------|-------|
| GET | /api/admin/staff/{user_id}/permissions | `staff:*:manage` |
| PUT | /api/admin/staff/{user_id}/permissions/overrides | `staff:*:manage` |

### Customer Lookup
| Method | Path | Guard |
|--------|------|-------|
| GET | /api/auth/users/lookup?email= | `bookings:*:create_on_behalf` |

### Customer Management
| Method | Path | Guard |
|--------|------|-------|
| GET | /api/admin/customers?search= | `customers:*:read` or `customers:*:manage` |
| POST | /api/admin/customers | `customers:*:manage` |
| PATCH | /api/admin/customers/{id} | `customers:*:manage` |
| POST | /api/admin/customers/{id}/deactivate | `customers:*:deactivate` |
| POST | /api/admin/customers/{id}/activate | `customers:*:manage` |

### Lister Management (new)
| Method | Path | Guard |
|--------|------|-------|
| GET | /api/admin/listers | `listers:*:read` |
| POST | /api/admin/listers | `listers:*:invite` |
| PATCH | /api/admin/listers/{user_id} | `listers:*:manage` |
| POST | /api/admin/listers/{user_id}/deactivate | `listers:*:manage` |
| POST | /api/admin/listers/{user_id}/activate | `listers:*:manage` |

## On-Behalf Booking Flow

1. Staff enters customer email
2. System looks up user by email (`GET /auth/users/lookup`) — **unscoped, always searches all customers**
3. If not found → staff provides name (required) + phone (optional)
4. Submit → `POST /bookings/on-behalf`
5. Service creates customer account if new (user_type=customer, is_verified=false, assigns customer role)
6. Checks `ResourceType.staff_booking_auto_confirm` for auto-confirm setting
7. Creates booking with resolved user_id

Note: Listers do NOT have `bookings:*:create_on_behalf` — the on-behalf flow is staff-only.

## Frontend

### usePermissions Hook
Location: `frontend/src/hooks/use-permissions.ts`
Derives from zustand auth store's `user.permissions`. Implements same superset/wildcard matching as backend.
Returns: `{ permissions, hasPermission, hasAnyPermission, canAccessNav, isLoading }`

### Auth Store Type Helpers

```ts
isAdmin: () => user?.user_type === "admin",
isStaff: () => user?.user_type === "staff",
isLister: () => user?.user_type === "lister",
```

### Components
- `PermissionAccordion` — accordion with switch toggles per permission, grouped by domain
- `PermissionOverrideEditor` — inline override list for staff edit sheet (grant/revoke per user)
- `StaffBookingSheet` — 3-step booking flow (customer → resource → schedule); only shown with `bookings:*:create_on_behalf`

### Pages
- `/admin/staff` — staff management with override editor in edit sheet
- `/admin/staff/listers` — list/manage listers under the current staff member
- `/admin/staff/roles` — role management with accordion permission UI
- `/admin/bookings` — "New Booking" button (permission-gated with `bookings:*:create_on_behalf`)
- `/admin/customers` — customer CRUD with booking drill-down dialog (permission-gated with `customers:*:read`)

### NAV_PERMISSION_MAP

Controls which nav items are visible per user based on their permissions:

```ts
"/admin/resources": ["resources:*:read", "resources:*:manage"],
"/admin/bookings": ["bookings:*:read", "bookings:*:manage"],
"/admin/customers": ["customers:*:read", "customers:*:manage"],
"/admin/reviews": ["reviews:*:read", "reviews:*:moderate"],
"/admin/staff": ["staff:*:manage", "listers:*:manage"],
"/admin/notifications": ["settings:*:manage"],
"/admin/theming": ["theme:*:read", "theme:*:edit"],
"/admin/settings": ["settings:*:manage"],
"/admin/payouts": ["settings:*:manage"],
```

### PERMISSION_DOMAIN_LABELS

```ts
customers: "Customers",
listers: "Listers",
resource_types: "Resource Types",
// ... plus existing domains
```

### Team Sub-Nav Structure

The Staff section is restructured into a "Team" sub-nav with three tabs:

```ts
"/admin/staff": {
  title: "Team",
  items: [
    { href: "/admin/staff", label: "Staff" },
    { href: "/admin/staff/listers", label: "Listers" },
    { href: "/admin/staff/roles", label: "Roles & Permissions" },
  ],
}
```

### Nav Visibility by User Type

| Nav item | admin | staff | lister | customer |
|----------|-------|-------|--------|----------|
| Resources | Yes | Yes | Yes (own) | No |
| Bookings | Yes | Yes | Yes (own resources) | Own |
| Customers | Yes | Yes | No | No |
| Reviews | Yes | Yes | Yes (own resources) | Own |
| Staff/Listers | Yes | Yes (listers tab) | No | No |
| Notifications | Yes | No | No | No |
| Theming | Yes | No | No | No |
| Settings | Yes | No | No | No |
| Payouts | Yes | No | No | No |

Visibility is driven by permissions — no special user_type logic in the frontend; if a user has the permission, the nav item appears.

## Database Migrations (Staff Isolation Redesign)

### Migration: Add `manager_id` to users

```sql
ALTER TABLE users ADD COLUMN manager_id UUID REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX ix_users_manager_id ON users(manager_id);
```

### Migration: Tenant isolation config

`staff_isolation_mode` added to tenant settings JSONB. Default: `"shared"`.

### Migration: Seed new permissions

New domains `customers` and `listers` are seeded, existing role permissions are preserved. Lister role created with restricted permission set.

### Migration Safety

- Default `staff_isolation_mode = "shared"` — zero behavior change on deploy
- `manager_id` is nullable — existing users unaffected
- New permissions are additive — existing role permissions preserved
- No existing columns removed or renamed
