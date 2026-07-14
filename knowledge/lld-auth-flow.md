# LLD: Auth & RBAC Flow

## JWT Token Structure

Source: `backend/app/core/auth/jwt.py`

### Access Token
```json
{
  "sub": "<user_id>",
  "tenant_id": "<tenant_uuid>",
  "roles": ["admin", "owner"],
  "type": "access",
  "exp": "<15 min from now>",
  "jti": "<uuid4>"
}
```
Algorithm: HS256. Secret: `SECRET_KEY` env var.

### Refresh Token
```json
{
  "sub": "<user_id>",
  "tenant_id": "<tenant_uuid>",
  "type": "refresh",
  "exp": "<7 days from now>",
  "jti": "<uuid4>"
}
```
Stored in Redis as `refresh:<jti>` → `<user_id>:<tenant_id>` with TTL = 7 days.

## Auth Sequence Diagrams

### Registration Flow
```
Client                    Backend                    Redis          Celery
  │ POST /auth/register     │                         │              │
  │ {email,password,name}   │                         │              │
  │─────────────────────────►                         │              │
  │                         │ Check email unique      │              │
  │                         │ (409 if exists)         │              │
  │                         │ Hash password (bcrypt)  │              │
  │                         │ INSERT user             │              │
  │                         │ Create access token     │              │
  │                         │ Create refresh token ──►│ SETEX        │
  │                         │                         │ refresh:<jti>│
  │                         │                         │              │
  │                         │ Queue welcome email ───────────────────►│
  │◄────────────────────────│                         │              │
  │ {access_token,          │                         │              │
  │  refresh_token}         │                         │              │
```

### Login Flow
```
Client                    Backend                    Redis
  │ POST /auth/login        │                         │
  │ {email, password}       │                         │
  │─────────────────────────►                         │
  │                         │ SELECT user by email    │
  │                         │ (401 if not found)      │
  │                         │ (403 if no password)    │
  │                         │ verify_password(bcrypt) │
  │                         │ (401 if mismatch)       │
  │                         │ (403 if !is_active)     │
  │                         │ UPDATE last_login       │
  │                         │ Create tokens ─────────►│ SETEX
  │◄────────────────────────│                         │
  │ {access_token,          │                         │
  │  refresh_token}         │                         │
```

### Token Refresh Flow (Rotation)
```
Client                    Backend                    Redis
  │ POST /auth/refresh      │                         │
  │ {refresh_token}         │                         │
  │─────────────────────────►                         │
  │                         │ Decode JWT              │
  │                         │ Check type="refresh"    │
  │                         │ Check JTI in Redis ────►│ EXISTS refresh:<jti>
  │                         │                    ◄────│ true/false
  │                         │ (401 if revoked)        │
  │                         │ DELETE old JTI ────────►│ DEL refresh:<old_jti>
  │                         │ Verify user exists      │
  │                         │ Create new token pair ─►│ SETEX refresh:<new_jti>
  │◄────────────────────────│                         │
  │ {new access_token,      │                         │
  │  new refresh_token}     │                         │
```
One-time use: old refresh token revoked before issuing new one.

### Logout Flow
```
Client                    Backend                    Redis
  │ POST /auth/logout       │                         │
  │ {refresh_token}         │                         │
  │─────────────────────────►                         │
  │                         │ Decode, get JTI         │
  │                         │ Revoke ────────────────►│ DEL refresh:<jti>
  │◄────────────────────────│                         │
  │ {"detail":"Logged out"} │                         │
```

### Staff Invite Flow
```
Admin                     Backend                    Redis          Celery
  │ POST /admin/staff       │                         │              │
  │ {email,name,roles}      │                         │              │
  │─────────────────────────►                         │              │
  │                         │ Create user (no pass)   │              │
  │                         │ Assign roles            │              │
  │                         │ Generate invite token   │              │
  │                         │ Store in Redis ────────►│ SETEX        │
  │                         │                         │ invite:<tok> │
  │                         │                         │ TTL=72h      │
  │                         │ Send invite email ─────────────────────►│
  │◄────────────────────────│                         │              │

Invitee                   Backend                    Redis
  │ GET /auth/verify-invite │                         │
  │ ?token=xxx              │                         │
  │─────────────────────────►                         │
  │                         │ GET invite:<tok> ──────►│
  │                         │                    ◄────│ {user_id,tenant_id}
  │◄────────────────────────│                         │
  │ {valid:true, email,name}│                         │
  │                         │                         │
  │ POST /auth/accept-invite│                         │
  │ {token, password}       │                         │
  │─────────────────────────►                         │
  │                         │ GETDEL invite:<tok> ───►│ (one-time claim)
  │                         │ Set password_hash       │
  │                         │ Activate user           │
  │                         │ Create tokens           │
  │◄────────────────────────│                         │
  │ {access_token,          │                         │
  │  refresh_token}         │                         │
```

## Request Auth Validation

Source: `backend/app/core/auth/dependencies.py`

`get_current_user()`:
1. Extract Bearer token from `Authorization` header
2. Decode JWT (401 if invalid/expired)
3. Check `type == "access"` (401 if not)
4. Get tenant context (401 if missing)
5. Compare `token.tenant_id` with `context.tenant.id` (403 if mismatch — cross-tenant attack prevention)
6. Load user from DB (401 if not found or inactive)

## RBAC Permission System

### Permission Format
```
domain:qualifier:action
```
Examples: `resources:own:create`, `bookings:any:read`, `reviews:*:moderate`

### Wildcard Matching

Source: `dependencies.py:matches_permission`

For required permission `domain:qualifier:action`, check against granted set:
1. Exact match
2. `domain:*:action` (any qualifier)
3. `domain:qualifier:*` (any action)
4. `domain:*:*` (any qualifier + action)
5. `*:*:*` (superuser)

### Admin Bypass

`user.user_type == "admin"` skips all permission checks entirely in `require_permission()`.

### Default Roles (seeded per tenant)

Created by `backend/app/core/auth/seed.py` during tenant provisioning:
- `admin` — full access (`*:*:*`)
- `owner` — resource management permissions
- `customer` — booking and review permissions

## Token Lifetimes

| Token | Default TTL | Config |
|-------|-----------|--------|
| Access | 15 min | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh | 7 days | `REFRESH_TOKEN_EXPIRE_DAYS` |
| Invite | 72 hours | `INVITE_TOKEN_EXPIRE_HOURS` |

## Frontend Auth (client-side)

Source: `frontend/src/lib/api.ts`

Axios interceptor handles 401 transparently:
1. On 401 response, check if already retrying
2. If not: get refresh token from store, call `POST /auth/refresh`
3. Update tokens in Zustand store
4. Retry original request with new access token
5. Queue concurrent requests while refreshing (failedQueue pattern)
6. If refresh fails: clear auth, redirect to login

## Admin Account Creation

Two paths to create admin accounts:

### 1. Platform-level Bootstrap (for initial seeding)

Endpoint: `POST /api/platform/bootstrap-admin`
Auth: Platform user JWT (Bearer token from `/api/platform/login`)

Creates an admin user directly in a tenant schema with password set, no invite flow.

```bash
# Step 1: Get platform token
TOKEN=$(curl -s http://localhost:8080/api/platform/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@rentmanager.com","password":"admin123"}' \
  | jq -r '.access_token')

# Step 2: Bootstrap admin
curl -s http://localhost:8080/api/platform/bootstrap-admin \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "tenant_id": "<tenant-uuid>",
    "email": "newadmin@example.com",
    "password": "securepassword123",
    "full_name": "Admin Name",
    "domain": "rm.networkingbyte.com"
  }'
```

Response:
```json
{
  "user_id": "<uuid>",
  "email": "newadmin@example.com",
  "full_name": "Admin Name",
  "tenant_id": "<tenant-uuid>",
  "tenant_name": "Test Tenant",
  "domain": "rm.networkingbyte.com",
  "roles": ["admin"]
}
```

Notes:
- Domain defaults to `rm.networkingbyte.com` if omitted
- Auto-creates TenantDomain mapping if domain not yet registered
- Multiple admins per domain supported
- 409 if email already exists in tenant or domain belongs to different tenant

### 2. Tenant-level Admin Invite (admin creates admin)

Endpoint: `POST /api/admin/staff`
Auth: Tenant admin JWT + `X-Tenant-ID` header (or domain-based resolution)

Existing admin invites another user as admin via the staff invite flow.

```bash
# Step 1: Login as existing tenant admin
TOKEN=$(curl -s http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: test-4a771ff5" \
  -d '{"email":"mohit@test.com","password":"password123"}' \
  | jq -r '.access_token')

# Step 2: Invite new admin
curl -s http://localhost:8080/api/admin/staff \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: test-4a771ff5" \
  -d '{
    "email": "newadmin@example.com",
    "full_name": "New Admin",
    "user_type": "staff",
    "role_slugs": ["admin"]
  }'
```

This sends an invite email. Invitee accepts via `/auth/accept-invite` to set password.

## Security Notes

- Password: bcrypt hashing (`passlib`)
- JWT: HS256 with shared secret (not asymmetric — single backend)
- Refresh tokens: one-time use (rotation), stored in Redis with TTL
- Cross-tenant: JWT tenant_id verified against request tenant context
- Rate limiting: registration endpoint (`30/minute` default)
- Platform superadmin: separate JWT, IP whitelist middleware
