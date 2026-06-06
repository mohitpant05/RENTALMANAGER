# LLD: API Contracts

Complete endpoint reference with request/response schemas, status codes, and auth requirements.

## Common Patterns

- All API paths prefixed with `/api/`
- Error format: `{"detail": "Error message"}` (string or list of validation errors)
- Auth: `Authorization: Bearer <access_token>` header
- Tenant: `X-Tenant-ID: <slug>` header (or subdomain/custom domain)
- Pagination: `offset` + `limit` query params
- UUIDs: all IDs are UUID v4

## Auth Endpoints (`/api/auth`)

### POST /api/auth/register (201)
Rate limited: configurable (default `30/minute`)
```
Request:  { email: EmailStr, password: str (≥8 chars), full_name: str, phone?: str }
Response: { access_token: str, refresh_token: str, token_type: "bearer" }
Errors:   409 "Email already registered"
```

### POST /api/auth/login
```
Request:  { email: EmailStr, password: str }
Response: { access_token: str, refresh_token: str, token_type: "bearer" }
Errors:   401 "Invalid email or password"
          403 "Account pending invite acceptance" (null password_hash)
          403 "Account is deactivated"
```

### POST /api/auth/refresh
```
Request:  { refresh_token: str }
Response: { access_token: str, refresh_token: str, token_type: "bearer" }
Errors:   401 "Invalid refresh token" | "Invalid token type" | "Refresh token revoked"
Side:     Old refresh token revoked (one-time use), new one issued
```

### POST /api/auth/logout
Auth required.
```
Request:  { refresh_token: str }
Response: { detail: "Logged out" }
Side:     Refresh token JTI deleted from Redis
```

### GET /api/auth/me
Auth required.
```
Response: { id, email, full_name, phone, is_active, is_verified, user_type, avatar_url, preferred_currency, created_at, roles: [str] }
```

### PATCH /api/auth/me
Auth required.
```
Request:  { full_name?, phone?, avatar_url?, preferred_currency? }  (all optional, partial update)
Response: UserResponse (same as /me)
```

### GET /api/auth/user/{user_id}
```
Response: UserResponse
Errors:   404 "User not found"
```

### GET /api/auth/verify-invite?token=...
```
Response: { valid: bool, email?: str, full_name?: str }
```

### POST /api/auth/accept-invite
```
Request:  { token: str, password: str (≥8 chars) }
Response: TokenResponse
Errors:   400 "Invalid or expired invite"
Side:     Sets password, activates user, marks verified, sends welcome email
```

---

## Resource Type Endpoints (`/api/resource-types`)

### GET /api/resource-types?active_only=true
```
Response: [{ id, name, slug, icon, description, availability_model, pricing_model, attribute_schema, slot_config, pricing_config, cancellation_defaults, commission_config, requires_verification, role, discovery_radius_km, display_order, is_active, created_at, updated_at }]
```

### GET /api/resource-types/templates
```
Response: { "template_slug": { slug, name, description }, ... }
```

### GET /api/resource-types/{slug}
```
Response: ResourceTypeResponse
Errors:   404
```

### POST /api/resource-types (201)
Permission: `resources:*:manage`
```
Request:  { name, slug, availability_model, pricing_model, attribute_schema?, slot_config?, pricing_config?, cancellation_defaults?, commission_config?, ... }
Response: ResourceTypeResponse
```

### POST /api/resource-types/from-template/{template_slug} (201)
Permission: `resources:*:manage`
```
Response: ResourceTypeResponse
Errors:   404 "Template not found"
```

### PUT /api/resource-types/{id}
Permission: `resources:*:manage`

### DELETE /api/resource-types/{id} (204)
Permission: `resources:*:manage`

---

## Resource Endpoints (`/api/resources`)

### GET /api/resources?type_id=&status=&offset=0&limit=50
```
Response: [ResourceResponse]
```

### GET /api/resources/{id}
```
Response: { id, type_id, name, description, location_lat, location_lng, location_address, attributes, base_price, currency, status, rating_avg, rating_count, owner_id, commission_config, version, created_at, updated_at }
```

### POST /api/resources (201)
Permission: `resources:*:create`. Sets `owner_id` from auth user.

### PUT /api/resources/{id}
Auth required. Owner or admin only.

### DELETE /api/resources/{id} (204)
Auth required. Owner or admin only.

### POST /api/resources/{id}/availability/check
```
Request:  { start: datetime, end: datetime }
Response: { available: bool, price: float }
```

### POST /api/resources/{id}/availability/hold
Auth required.
```
Request:  { start: datetime, end: datetime, hold_minutes?: int (default 10) }
Response: { hold_token: str, expires: datetime, price: float }
Errors:   ValueError → 400 if time overlap detected
Side:     Creates ResourceAvailability record with status="held"
```

### POST /api/resources/{id}/availability/release
Auth required.
```
Request:  { hold_token: str }
Response: { detail: "Hold released" }
```

### POST /api/resources/{id}/price
```
Request:  { start: datetime, end: datetime }
Response: { price: float, currency: str }
```

### GET /api/resources/{id}/addons?start_date=&end_date=
```
Response: list of available addon resources with availability + pricing
```

### Resource Assignments (admin)
- GET /api/resources/{id}/assignments — Permission: `resources:*:manage`
- POST /api/resources/{id}/assignments (201) — `{ addon_resource_id, priority }`
- PATCH /api/resources/{id}/assignments/{assignment_id} — `{ priority }`
- DELETE /api/resources/{id}/assignments/{assignment_id} (204)

---

## Booking Endpoints (`/api/bookings`)

### POST /api/bookings (201)
Auth required.
```
Request:  { resource_id: UUID, hold_token: str, start_time: datetime, end_time: datetime, notes?: str, auto_confirm: bool (default true), user_id?: UUID (admin only) }
Response: BookingResponse
Errors:   404 "Resource not found", 400 "Resource is not active", 409 "Hold token invalid or expired", 403 "Only admins can book on behalf"
```

### GET /api/bookings/mine?status=&offset=0&limit=50
Auth required. Own bookings only.

### GET /api/bookings?status=&resource_id=&offset=0&limit=50
Auth required. Admin sees all; non-admin sees own only.

### GET /api/bookings/{id}
Auth required. Admin or booking owner.
```
Errors: 403 "Not the booking owner"
```

### POST /api/bookings/{id}/confirm
Permission: `bookings:*:manage`
```
Errors: 409 "Cannot confirm booking in '{status}' state"
```

### POST /api/bookings/{id}/reject
Permission: `bookings:*:manage`
```
Request:  { reason?: str }
Side:     Releases hold if exists
```

### POST /api/bookings/{id}/cancel
Auth required.
```
Request:  { reason?: str }
Errors:   403 "Not the booking owner" (non-admin), 409 invalid transition
Side:     Calculates refund %, releases hold, cascade-cancels addon bookings
```

### POST /api/bookings/{id}/no-show
Permission: `bookings:*:manage`
```
Side: Sets refund_percent=0
```

### POST /api/bookings/bundled (201)
Auth required.
```
Request:  { primary: BookingItemCreate, addons: [BookingItemCreate] }
Response: { group_id: UUID, primary: BookingResponse, addons: [BookingResponse] }
```

### POST /api/bookings/{id}/add-addon (201)
Permission: `resources:*:assign_for_customer`
```
Request:  { resource_id, hold_token, start_time, end_time, notes?, auto_confirm? }
Errors:   400 "Cannot add addon to an addon booking", 400 "Primary booking must be pending or confirmed"
```

---

## Payment Endpoints (`/api/payments`)

### POST /api/payments/booking/{booking_id} (201)
Auth required.
```
Response: { id, booking_id, amount, currency, provider, status, provider_ref, provider_data, paid_at, refund_amount, refunded_at, created_at, updated_at }
Errors:   404 "Booking not found", 409 "Payment already exists for this booking"
```

### GET /api/payments/booking/{booking_id}
Auth required.
```
Errors: 404 "No payment found for this booking"
```

### POST /api/payments/{id}/mark-paid
Permission: `*:*:*` (admin only)
```
Request:  { notes?: str }
Errors:   409 "Cannot mark as paid: status is '{status}'"
Side:     Sets status="paid", paid_at=now
```

### POST /api/payments/{id}/refund
Permission: `*:*:*` (admin only)
```
Request:  { amount?: float, reason?: str }
Errors:   409 "Cannot refund: status is '{status}'", 400 "Refund amount exceeds payment amount", 502 "Provider refund failed"
Side:     Calls provider refund API, sets status="refunded" or "partially_refunded"
```

---

## Search Endpoints (`/api/search`)

### POST /api/search
No auth required (public).
```
Request:  { q: str, resource_type_slug?: str, filters?: dict, geo_lat?: float, geo_lng?: float, geo_radius_km?: float, sort_by?: str, sort_order?: "asc"|"desc", offset: int, limit: int }
Response: { hits: [SearchHit], query: str, processing_time_ms: int, estimated_total_hits: int, offset: int, limit: int }
```
If no `resource_type_slug`, searches across all active primary/standalone resource types.

---

## Notification Endpoints (`/api/notifications`)

### GET /api/notifications?unread_only=false&offset=0&limit=20
Auth required.

### GET /api/notifications/unread-count
Auth required. → `{ count: int }`

### POST /api/notifications/{id}/read
Auth required. → NotificationResponse

### POST /api/notifications/read-all
Auth required. → `{ marked: int }`

---

## Storage Endpoints (`/api/storage`)

### POST /api/storage/upload (201)
Auth required. Backend-proxied (browser never contacts MinIO directly).
```
Request:  multipart/form-data
          file: File (image/jpeg, image/png, image/webp, image/gif, max 10MB)
          entity_type: str
          entity_id: UUID
          purpose: str = "image"
Response: AttachmentResponse with download_url
Errors:   400 "Unsupported file type" | "File too large"
```

### GET /api/storage/attachments?entity_type=&entity_id=
Auth required.

### GET /api/storage/attachments/{id}
Auth required.

### DELETE /api/storage/attachments/{id} (204)
Auth required. Owner or admin.

---

## Review Endpoints (`/api/reviews`)

### POST /api/reviews (201) — customer → resource review
### POST /api/reviews/lister (201) — lister → customer review
Auth required.
```
Request:  ReviewCreate schema
Response: ReviewResponse
```

### GET /api/reviews?resource_id=&direction=&offset=0&limit=20
Optional auth.

### GET /api/reviews/my?direction=&offset=0&limit=20
Auth required.

### GET /api/reviews/resource/{resource_id}/summary
```
Response: ResourceRatingResponse
```

### POST /api/reviews/{id}/moderate
Permission: `reviews:*:moderate`
```
Request: { status: str, reason?: str }
```

---

## Admin Endpoints (`/api/admin`)

All require `*:*:*` permission (admin user_type).

- GET /api/admin/tenant → TenantResponse
- PATCH /api/admin/tenant → update name, base_currency, timezone, config
- GET/PUT /api/admin/theme → TenantTheme
- GET/POST/DELETE /api/admin/domains → custom domain CRUD
- GET /api/admin/staff → list staff users
- POST /api/admin/staff → invite staff (creates user with null password, sends invite email)
- POST /api/admin/staff/{id}/deactivate
- POST /api/admin/staff/{id}/activate
- GET /api/admin/staff/{id}/deactivation-impact

---

## Platform Superadmin Endpoints (`/api/platform`)

Separate auth (PlatformUser + SuperadminIPMiddleware).

- POST /api/platform/login → PlatformTokenResponse (rate limited 5/15min)
- POST /api/platform/validate-key → validates superadmin secret key
- GET/POST /api/platform/tenants → list/create tenants
- GET /api/platform/tenants/{id}
- POST /api/platform/tenants/{id}/deactivate|activate
- GET/POST/PUT/DELETE /api/platform/tenants/{id}/domains
- GET/PUT /api/platform/tenants/{id}/theme
- GET /api/platform/dashboard/stats → { total_tenants, active_tenants, total_users, total_bookings, services health }
- GET/PUT /api/platform/settings → platform-wide key/value config

---

## Commission Endpoints (`/api/commission`)

- GET /api/commission/resource-type/{id} — get commission config for type
- PUT /api/commission/resource-type/{id} — update commission config
- GET /api/commission/resource/{id} — get effective commission (resource override → type fallback)
- PUT /api/commission/resource/{id} — set resource-level override
- POST /api/commission/preview — preview breakdown for amount

---

## Currency Endpoints (`/api/currency`)

No auth required (tenant-free path).
- GET /api/currency/rates → exchange rates
- GET /api/currency/convert?from=&to=&amount= → converted amount

---

## Tenant-Free Paths (no X-Tenant-ID required)

- `/api/health`, `/api/health/*`
- `/api/docs`, `/api/openapi.json`, `/api/redoc`
- `/api/tenancy/resolve`
- `/api/platform/*`
- `/api/currency/*`
- `/api/payments/webhook/*`
