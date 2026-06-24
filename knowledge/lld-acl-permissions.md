# ACL & Permission System

## Overview

Role-based access control (RBAC) with per-user permission overrides. Every protected endpoint uses permission checks instead of `user_type` comparisons.

## Permission Format

`domain:qualifier:action` — e.g. `bookings:*:confirm`

## Permission Hierarchy (Supersets)

`bookings:*:manage` automatically grants:
- `bookings:*:confirm`
- `bookings:*:reject`
- `bookings:*:cancel`
- `bookings:*:no_show`

Admin users have `*:*:*` which bypasses all checks.

## Permission Resolution Order

1. Check `UserPermissionOverride` for user+permission — if exists, use `granted` value (true=grant, false=revoke)
2. Else check role-based permissions via `RolePermission` join
3. Admin (`user_type == "admin"`) gets `{"*:*:*"}` and bypasses all checks

## Key Dependency

`get_current_user_with_perms()` in `backend/app/core/auth/dependencies.py` returns `tuple[User, set[str]]`. Used by booking router and any endpoint needing permission checks.

`matches_permission(required, granted)` checks exact match, wildcard candidates, AND superset hierarchy.

## All Permissions (26 total)

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

## Default Roles

| Role | Key Permissions |
|------|----------------|
| admin | `*:*:*` (all) |
| staff | resources (read/create/manage), bookings (read/manage/confirm/reject/no_show), reviews, pricing read, analytics |
| customer | resources read, bookings (read/create), reviews (read/create) |
| lister | resources (read/create/manage), bookings (read/manage/confirm/reject), reviews read, pricing read |

## Data Model

### UserPermissionOverride (composite PK: user_id + permission_id)
- `user_id` UUID FK→users
- `permission_id` UUID FK→permissions
- `granted` bool (true=grant beyond role, false=revoke from role)
- `created_at` datetime

### ResourceType addition
- `staff_booking_auto_confirm` bool (default true) — controls whether staff-created bookings auto-confirm

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

## On-Behalf Booking Flow

1. Staff enters customer email
2. System looks up user by email (`GET /auth/users/lookup`)
3. If not found → staff provides name (required) + phone (optional)
4. Submit → `POST /bookings/on-behalf`
5. Service creates customer account if new (user_type=customer, is_verified=false, assigns customer role)
6. Checks `ResourceType.staff_booking_auto_confirm` for auto-confirm setting
7. Creates booking with resolved user_id

## Frontend

### usePermissions Hook
Location: `frontend/src/hooks/use-permissions.ts`
Derives from zustand auth store's `user.permissions`. Implements same superset/wildcard matching as backend.
Returns: `{ permissions, hasPermission, hasAnyPermission, canAccessNav, isLoading }`

### Components
- `PermissionAccordion` — accordion with switch toggles per permission, grouped by domain
- `PermissionOverrideEditor` — inline override list for staff edit sheet (grant/revoke per user)
- `StaffBookingSheet` — 3-step booking flow (customer → resource → schedule)

### Pages
- `/admin/staff/roles` — role management with accordion permission UI
- `/admin/staff` — staff management with override editor in edit sheet
- `/admin/bookings` — "New Booking" button (permission-gated with `bookings:*:create_on_behalf`)
