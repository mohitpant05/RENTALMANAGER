# RentManager — Multi-Tenant White-Label Rental Management Platform

## Overview

A generic, white-label, multi-tenant rental marketplace platform. Tenants (businesses) create fully branded instances to list and rent any type of resource — apartments, vehicles, cooks, restaurant tables, trash vans, equipment, or any custom category. Each resource type is admin-defined with dynamic attributes, availability models, and pricing strategies.

Three independent user segments: tourists/travelers, locals, and B2B operators (fleet owners, property managers, service providers).

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 15 (App Router + Server Components) | SSR for SEO, modern React |
| UI | Tailwind CSS v4 + shadcn/ui | Themeable component library |
| State | Zustand + TanStack Query | Client state + server data fetching |
| Backend | FastAPI + Pydantic v2 | Async API framework |
| ORM | SQLModel + Alembic | Type-safe ORM + migrations |
| Database | PostgreSQL 17 | Schema-per-tenant isolation |
| Cache | Redis 7 / Valkey | Caching, pub/sub, sessions |
| Search | Meilisearch | Full-text, geo, faceted filtering |
| File Storage | MinIO (self-hosted) → AWS S3 | Images, documents, verification files |
| Background Jobs | Celery + Redis | Async task processing |
| Real-time | FastAPI WebSockets + Redis pub/sub | Chat, notifications |
| API Gateway | Traefik | Tenant routing, rate limiting, SSL |
| Auth | JWT + OAuth2 (FastAPI built-in) | Tenant-scoped tokens |
| Maps | Mapbox or Leaflet + OpenStreetMap | Geo search, map view |
| Email | AWS SES or self-hosted Postal | Transactional email |
| SMS/WhatsApp | Twilio / WhatsApp Business API | Tenant-provided API keys |
| ID Verification | Onfido / Veriff | Identity verification badges |
| Currency | Exchange Rate API | Multi-currency conversion |
| Calendar | iCal / Google Calendar API | Availability sync |
| PDF | WeasyPrint | Invoices, booking confirmations |
| i18n | next-intl + Python gettext | Multi-language |
| Testing | pytest, Playwright, Vitest, Locust | Unit, E2E, load |
| Code Quality | Ruff, ESLint, Prettier, pre-commit | Linting, formatting |
| Error Tracking | Sentry | Frontend + backend errors |
| Analytics | PostHog (self-hosted) | User behavior, funnels |
| Feature Flags | Unleash (self-hosted) | Phased rollouts, per-tenant gating |
| Monitoring | Prometheus + Grafana | Metrics, alerting |
| Logging | Loki | Centralized logs |
| IaC | Terraform | Infrastructure as code |
| CI/CD | GitHub Actions | Build, test, deploy |
| Containers | Docker + Kubernetes (k3s → EKS) | Orchestration |
| Container Registry | AWS ECR | Docker image storage |
| AI (Phase 2) | LangChain + Anthropic SDK + LangGraph | Agentic concierge + admin intelligence |

### Future extraction targets (Go)

When scale demands, these modules are designed for extraction into Go microservices:
- Chat/messaging service (high concurrency WebSocket handling)
- Notification dispatcher (high throughput, low logic)
- API gateway / proxy layer

Module interfaces are designed with this extraction in mind — protocol-based contracts, no tight coupling.

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    CLIENTS                           │
│  Next.js Web App (SSR + SPA, PWA-ready)             │
│  [Tenant-resolved theming, responsive]              │
│  Mobile apps (Phase 4 — React Native)               │
└──────────────────────┬──────────────────────────────┘
                       │
              ┌────────▼────────┐
              │  API Gateway     │
              │  (Traefik)       │
              │  Tenant routing  │
              │  Rate limiting   │
              │  SSL termination │
              └────────┬────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              FASTAPI MODULAR MONOLITH                │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │ Generic Resource Engine                      │    │
│  │ (admin-defined resource types with dynamic   │    │
│  │  attributes, availability, pricing)          │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────┐ ┌──────────┐ ┌────────────┐           │
│  │ Auth/   │ │ Tenancy  │ │ Pricing    │           │
│  │ RBAC    │ │ Engine   │ │ Engine     │           │
│  └─────────┘ └──────────┘ └────────────┘           │
│  ┌─────────┐ ┌──────────┐ ┌────────────┐           │
│  │ Booking │ │ Reviews/ │ │ Search/Geo │           │
│  │ Engine  │ │ Trust    │ │            │           │
│  └─────────┘ └──────────┘ └────────────┘           │
│  ┌─────────┐ ┌──────────┐ ┌────────────┐           │
│  │ Notif.  │ │Chat (WS) │ │Verification│           │
│  │ Service │ │→ Go later│ │            │           │
│  └─────────┘ └──────────┘ └────────────┘           │
│  ┌─────────────────────────────────────────────┐    │
│  │ AI Agent Layer (Phase 2)                     │    │
│  │ Concierge + Admin Intelligence + Recommender │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
   ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
   │PostgreSQL│   │   Redis   │  │Meili-   │
   │(schema-  │   │Cache+PubSub│  │search   │
   │per-tenant)│   └───────────┘  └─────────┘
   └──────────┘
```

### Module communication rules

- Resource engine is generic — no hardcoded resource types
- Booking engine calls resource availability through abstract interface (strategy pattern)
- Chat module behind interface layer — swappable to Go service
- Modules communicate through service interfaces only — no direct model imports across boundaries
- All cross-module calls go through defined service interfaces

## Multi-Tenancy

### Tenant isolation: PostgreSQL schema-per-tenant

```
public schema (shared)
├── tenants              — tenant registry, config, subscription status
├── tenant_domains       — custom domain mappings
├── tenant_themes        — full theming config (colors, logos, fonts, components)
├── exchange_rates       — currency conversion rates
└── platform_config      — platform-wide settings

tenant_<uuid> schema (per tenant)
├── users                — tenant-scoped users
├── roles                — custom RBAC roles
├── permissions          — granular permissions
├── user_roles           — user-role mapping
├── resource_types       — admin-defined resource categories
├── resources            — all rentable resources (generic)
├── resource_availability — availability records (strategy varies by type)
├── bookings             — unified booking table
├── booking_items        — line items per booking
├── reviews              — two-way reviews
├── verifications        — ID verification, inspection badges
├── notifications        — notification log
├── chat_rooms           — conversation threads
├── chat_messages        — messages
├── pricing_rules        — admin-configured pricing strategies
├── currencies           — tenant-supported currencies
├── cancellation_policies — admin-configured per resource type
└── audit_log            — all state changes
```

### Tenant resolution (order of precedence)

1. Custom domain lookup (`rentals.clientbrand.com` → tenant_id)
2. Subdomain (`client.rentmanager.com` → tenant_id)
3. Header (`X-Tenant-ID` — for API consumers)

Once resolved → set PostgreSQL `search_path` to tenant schema for entire request lifecycle.

### Timezone & currency

- All timestamps stored in UTC
- `timezone` field on tenant + user for display conversion
- Base currency per tenant — prices stored in tenant's base currency
- Multi-currency display — converted at display time using exchange rates
- Exchange rates refreshed every 6 hours via Celery periodic task

## Generic Resource Engine

The platform does not hardcode resource types. Admins define custom resource categories with dynamic attributes, availability models, and pricing strategies.

### Resource type definition (admin creates)

```json
{
  "name": "Restaurant Tables",
  "slug": "restaurant-tables",
  "icon": "utensils",
  "availability_model": "time_slot",
  "slot_config": {
    "duration_options": ["1h", "1.5h", "2h"],
    "buffer_between": "30min"
  },
  "attributes": [
    {"name": "seats", "type": "number", "required": true, "filterable": true},
    {"name": "location", "type": "enum", "options": ["indoor", "outdoor", "rooftop"], "filterable": true},
    {"name": "cuisine_type", "type": "tags", "filterable": true}
  ],
  "pricing_model": "fixed_per_slot",
  "cancellation_defaults": {
    "free_cancel_hours": 4,
    "no_refund_after": true
  },
  "requires_verification": false
}
```

### Pre-built templates

Venues, vehicles, and cooks ship as pre-built resource type templates. Admin can use as-is, customize, or create entirely new types.

### Supported pricing models

| Model | Use case | How it works |
|-------|----------|-------------|
| `fixed_per_day` | Apartments, equipment | Flat daily rate |
| `fixed_per_slot` | Restaurant tables, cooks | Price per time slot |
| `per_hour` | Bikes, cars, trash vans | Hourly rate × duration |
| `tiered` | Long-term discounts | Different rates for day 1-3, 4-7, 8+ |
| `custom` | Complex pricing | Admin defines pricing formula via rules engine |

Admin selects pricing model per resource type. Can override at individual resource level.

### Tenant onboarding

- Self-service signup: business registers → creates tenant → gets subdomain
- Platform superadmin approves (or auto-approve based on platform config)
- Onboarding wizard: brand setup → resource types → first resources → go live
- Custom domain mapping added post-onboarding via admin panel

### Availability strategies

| Strategy | Use case | How it works |
|----------|----------|-------------|
| `date_range` | Apartments, venues, equipment | Check-in/check-out dates, no overlapping ranges |
| `time_slot` | Cooks, restaurant tables, consultants | Predefined slots with optional buffer time |
| `hourly` | Bikes, cars, trash vans, gear | Start time + duration, continuous time windows |

Each strategy implements a common interface:

```python
class AvailabilityProvider(Protocol):
    async def check(self, resource_id, start, end) -> bool
    async def hold(self, resource_id, start, end) -> HoldToken
    async def release(self, hold_token: HoldToken) -> None
    async def confirm(self, hold_token: HoldToken) -> None
```

### Dynamic attributes via JSONB

```sql
resource_types:
  id, tenant_id, name, slug, icon, availability_model,
  attribute_schema (JSONB), pricing_model, cancellation_config

resources:
  id, tenant_id, type_id, name, description, location (geo),
  attributes (JSONB), base_price, currency, status, rating, version
```

JSONB chosen over EAV for better query performance and simpler code. PostgreSQL GIN indexes on JSONB fields for filtering.

### Search auto-adapts

- Admin creates resource type → Meilisearch index auto-created
- `filterable: true` attributes → become facet filters in search UI
- Search UI renders dynamic filter panels from attribute schema

## Auth & RBAC

### User hierarchy

```
Platform Superadmin          — manages all tenants, onboarding, platform config
  └── Tenant Admin           — manages own tenant: resources, staff, theming, pricing
       └── Tenant Staff      — custom roles per tenant
            └── Customer     — books resources, leaves reviews
                └── Lister   — lists resources (B2B vendors within a tenant)
```

### Permission model

```
Format: <domain>:<resource_qualifier>:<action>

Examples:
  resources:*:read               — read all resources
  resources:vehicles:manage      — manage vehicle-type resources only
  resources:zone_north:manage    — manage resources in zone_north only
  bookings:*:cancel              — cancel any booking
  pricing:*:configure            — configure pricing rules
  staff:*:invite                 — invite staff members
  theme:*:edit                   — edit tenant theming
  reviews:*:moderate             — moderate reviews
```

- Tenant admin creates custom roles — groups of permissions
- Roles assigned to staff users
- Resource-level scoping via optional resource qualifier
- Permission check: `has_permission(user, "resources:zone_north:manage")`

### Token structure (JWT)

```json
{
  "sub": "user_uuid",
  "tenant_id": "tenant_uuid",
  "roles": ["fleet_manager"],
  "type": "access",
  "exp": 1234567890
}
```

- Access token: 15min TTL
- Refresh token: 7 days, stored in Redis, revocable
- OAuth2 support: Google, Apple login for customers

## Booking Flow & State Machine

```
DRAFT → PENDING → CONFIRMED → ACTIVE → COMPLETED
                 ↘ REJECTED
         CONFIRMED ↘ CANCELLED
         ACTIVE ↘ NO_SHOW
```

### States

| State | Trigger | Description |
|-------|---------|-------------|
| DRAFT | User selects resource + dates | Cart-like state |
| PENDING | User submits booking | Awaiting confirmation |
| CONFIRMED | Auto-confirm or lister/admin confirms | Booking locked in |
| REJECTED | Lister/admin declines | Booking denied |
| ACTIVE | Booking start time reached | Currently in use |
| COMPLETED | Booking end time reached | Done — triggers review prompt |
| CANCELLED | User or admin cancels | Subject to cancellation policy |
| NO_SHOW | User didn't show up | Marked by lister/admin |

### Conflict prevention

- Optimistic locking — `version` column on availability records
- Short-lived hold (admin-configurable, default 10min) — resource reserved while user completes booking
- Hold expires → auto-release back to available pool via Celery periodic cleanup

### Cancellation policy (admin-configurable per resource type or per resource)

```json
{
  "free_cancel_hours": 48,
  "partial_cancel_hours": 12,
  "partial_refund_percent": 50,
  "no_refund_after": true
}
```

Admin can set defaults at resource type level and override per individual resource.

### Payments

MVP: booking-only, no payment processing. Architecture reserves space for payment integration in Phase 3 (Stripe Connect or similar platform payments with commission model).

## Search & Discovery

### Meilisearch indexes (per tenant, per resource type)

Created dynamically when admin adds a resource type.

- Searchable: name, description, location, dynamic attributes
- Filterable: price, rating, availability, dynamic filterable attributes
- Sortable: price, rating, distance
- Geo: radius from point, bounding box for map view

### Features

- Map + list toggle — same query, different rendering
- Faceted filtering — dynamic per resource type from attribute schema
- Typo tolerance — Meilisearch built-in
- Instant search — sub-50ms responses
- Location autocomplete via Mapbox/OSM
- Saved searches — user can save search criteria

### Sync strategy

- DB → Meilisearch via Celery job on resource create/update/delete
- Full reindex nightly as safety net
- Availability filtering done post-search against DB for real-time accuracy

## White-Label Theming Engine

### Customizable per tenant

```json
{
  "brand": {
    "name": "CityRentals",
    "logo_url": "/storage/tenant_abc/logo.svg",
    "favicon_url": "/storage/tenant_abc/favicon.ico"
  },
  "colors": {
    "primary": "#2563eb",
    "secondary": "#7c3aed",
    "accent": "#f59e0b",
    "background": "#ffffff",
    "surface": "#f8fafc",
    "text_primary": "#0f172a",
    "text_secondary": "#64748b",
    "error": "#ef4444",
    "success": "#22c55e"
  },
  "typography": {
    "font_family": "Inter",
    "heading_font": "Plus Jakarta Sans",
    "base_size": "16px",
    "border_radius": "8px"
  },
  "components": {
    "button_style": "rounded",
    "card_shadow": true,
    "navbar_position": "top",
    "footer_layout": "standard"
  },
  "features": {
    "enabled_resource_types": ["venues", "vehicles", "cooks"],
    "reviews_enabled": true,
    "chat_enabled": true,
    "verification_required": false
  },
  "locale": {
    "default_language": "en",
    "supported_languages": ["en", "es", "fr"],
    "default_currency": "USD",
    "timezone": "America/New_York"
  }
}
```

### How it works

1. Tenant resolution → fetch theme config from Redis cache (DB fallback)
2. Next.js server component injects CSS variables from theme config
3. Tailwind CSS v4 uses CSS variables → entire UI adapts dynamically
4. `features.enabled_resource_types` toggles which resource types show in navigation, search, and menus
5. Admin panel includes live theme editor with instant preview

## Notification & Communication

### Multi-channel notification system

```
Event → Notification Service → Channel Router → [In-App, Email, SMS, WhatsApp]
```

- Tenant configures which channels per event type
- Tenant provides own API keys for SMS (Twilio) and WhatsApp
- Templates customizable per tenant per event
- In-app notifications always active (no external key needed)
- User-level notification preferences (opt-out per channel)

### Chat system

- WebSocket via FastAPI (→ Go extraction candidate)
- Redis pub/sub for multi-pod message fanout
- Room types: 1-to-1 (user ↔ lister), group (booking participants)
- Message types: text, image, booking reference, location share
- Typing indicators, read receipts, online status
- History persisted in DB, recent messages cached in Redis

## Verification & Trust

### User verification levels

| Level | Name | What |
|-------|------|------|
| 0 | Unverified | Email confirmed only |
| 1 | Basic | Phone verified |
| 2 | ID Verified | Government ID via Onfido/Veriff |
| 3 | Background Check | Extended check (for cooks, drivers) |

### Resource verification

- Inspection badges — admin/staff marks inspected + date
- Listing accuracy — staff confirms listing matches reality
- Certification verified — uploaded certificates admin-approved

### Review system

- Post-booking only (prevents fake reviews)
- Two-way: user reviews resource, lister reviews user
- Rating: 1-5 stars + configurable categories per resource type
- Review moderation — flagging + admin approval queue
- Trust score = f(verification_level, avg_rating, booking_history)

## Error Handling & Resilience

### Backend

- Global exception handler → structured JSON error responses
- Circuit breaker on external services (Onfido, Twilio, exchange rate API)
- Retry with exponential backoff for transient failures
- Dead letter queue for failed Celery jobs
- Request ID tracing across all logs (correlation ID in headers)

### Booking safety

- Optimistic locking (version column) prevents double-booking
- 10min hold with auto-expire prevents resource starvation
- Idempotency keys (reserved for phase 2 payment integration)

### Multi-tenancy safety

- Middleware enforces schema isolation — no cross-tenant data leak possible
- Row-level security as defense-in-depth layer
- Tenant context injected at middleware level, never trusted from client
- Integration tests verify isolation across 2+ tenant schemas

## Testing Strategy

| Layer | Tool | Scope |
|-------|------|-------|
| Unit | pytest | Service logic, pricing engine, availability checks, RBAC |
| Integration | pytest + testcontainers | DB operations, tenant isolation, search sync |
| API | pytest + httpx | Endpoint contracts, auth flows, error responses |
| Frontend unit | Vitest + React Testing Library | Components, hooks, stores |
| E2E | Playwright | Full booking flow, admin flows, multi-tenant theming |
| Load | Locust | Concurrent bookings, search under load |

Tenant isolation test suite: every integration test runs against 2+ tenant schemas to verify zero data leakage.

## Deployment Architecture

### Phase 1: EC2 + k3s

- Single EC2 instance running k3s (lightweight Kubernetes)
- All services as K8s pods: FastAPI, Celery workers, PostgreSQL, Redis, Meilisearch, MinIO
- Traefik as Ingress controller
- Monitoring: Prometheus + Grafana + Loki
- Daily DB backups → S3
- CI/CD: GitHub Actions → build images → push to ECR → rolling deploy

### Phase 2: EKS migration (post-funding)

- Managed Kubernetes (EKS)
- RDS for PostgreSQL (managed backups, replicas)
- ElastiCache for Redis
- S3 replaces MinIO
- CloudFront CDN for static assets
- Same K8s manifests — minimal migration effort

## Project Structure

```
rental-manager/
├── docker-compose.yml
├── terraform/
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   │
│   │   ├── core/
│   │   │   ├── auth/
│   │   │   ├── rbac/
│   │   │   ├── tenancy/
│   │   │   ├── theming/
│   │   │   ├── pricing/
│   │   │   ├── currency/
│   │   │   ├── notifications/
│   │   │   ├── search/
│   │   │   ├── storage/
│   │   │   ├── audit/
│   │   │   └── common/
│   │   │
│   │   ├── domains/
│   │   │   └── resources/
│   │   │       ├── models.py
│   │   │       ├── schemas.py
│   │   │       ├── service.py
│   │   │       ├── router.py
│   │   │       ├── type_registry.py
│   │   │       ├── attributes.py
│   │   │       └── availability/
│   │   │           ├── strategy.py
│   │   │           ├── date_range.py
│   │   │           ├── time_slot.py
│   │   │           ├── hourly.py
│   │   │           └── calendar.py
│   │   │
│   │   ├── booking/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── router.py
│   │   │   └── state_machine.py
│   │   │
│   │   ├── reviews/
│   │   ├── chat/
│   │   ├── verification/
│   │   │
│   │   └── ai/                     # Phase 2
│   │       ├── concierge/
│   │       ├── recommendations/
│   │       └── admin_intelligence/
│   │
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── (public)/
│   │   │   ├── (auth)/
│   │   │   ├── (dashboard)/
│   │   │   ├── (admin)/
│   │   │   └── (superadmin)/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── booking/
│   │   │   ├── search/
│   │   │   ├── maps/
│   │   │   └── chat/
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   ├── auth/
│   │   │   └── theme/
│   │   ├── stores/
│   │   └── styles/
│   │
│   └── tests/
│       ├── unit/
│       └── e2e/
│
└── docs/
```

## AI Phase 2 Architecture

### User-facing: Concierge Agent

- Trip planner: user describes needs → AI suggests resource package (apartment + vehicle + cook)
- During-trip suggestions: weather-aware, context-aware proactive alerts
- Rebooking assistance: plans change → AI handles cancellation + rebooking
- Built with LangGraph for multi-step agent workflows
- Uses booking history + preferences for personalization

### Admin-facing: Intelligence Dashboard

- Pricing optimization: demand forecasting, suggested price adjustments
- Inventory suggestions: "high demand for bikes in zone X, consider adding more"
- Occupancy analytics: utilization rates, peak patterns
- Review sentiment analysis: aggregate feedback trends

### Recommendation Engine

- Collaborative filtering: "users who booked X also liked Y"
- Content-based: match resource attributes to user preferences
- Personalized search ranking based on user history

### AI integration architecture

- Separate module within modular monolith (`app/ai/`)
- Reads from main DB (read replicas when on RDS)
- Does not modify core booking/resource logic — observes and recommends
- Feature-flagged per tenant via Unleash
- Can be extracted into standalone Python service if compute demands require it

## Phasing

### Phase 1 — MVP

- Multi-tenant setup with schema isolation
- Tenant onboarding + white-label theming
- Generic resource engine with 3 pre-built templates (venues, vehicles, cooks)
- Booking engine with state machine
- Auth + RBAC (custom roles + resource-level permissions)
- Search + map view (Meilisearch)
- Basic notifications (in-app + email)
- Reviews (two-way)
- Admin panel (resource management, staff, theming, pricing config)
- Docker + k3s deployment on EC2
- CI/CD pipeline

### Phase 2 — Trust & Communication

- ID verification integration (Onfido/Veriff)
- Real-time chat (WebSocket)
- SMS/WhatsApp notifications (tenant-provided keys)
- Calendar sync (iCal, Google Calendar)
- PDF generation (invoices, booking confirmations)
- Advanced analytics (PostHog)

### Phase 3 — Payments & Scale

- Payment integration (Stripe Connect or equivalent)
- Commission model / platform fees
- Multi-currency payment processing
- EKS migration
- CDN (CloudFront)
- Managed database (RDS)

### Phase 4 — AI & Intelligence

- Recommendation engine
- Concierge agent (trip planning)
- Admin intelligence dashboard
- Proactive suggestions
- Go extraction of chat/notification services (if scale demands)
- Mobile apps (React Native)
