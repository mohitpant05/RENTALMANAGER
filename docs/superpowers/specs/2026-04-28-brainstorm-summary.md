# Brainstorm Summary — RentManager Platform

**Date:** 2026-04-28
**Participants:** Mohit Pant + Claude

## What We Built

Design spec for a **multi-tenant, white-label rental management platform** — a generic marketplace where any business can create a branded instance to rent any type of resource.

## Key Decisions Made

### Business Model
- **Target users:** All — tourists, locals, B2B operators (full marketplace)
- **Multi-tenancy:** White-label with full theming (colors, logos, fonts, buttons, everything customizable)
- **Pricing:** Admin-configurable per resource type (5 models: fixed/day, fixed/slot, per hour, tiered, custom)
- **Payments:** Booking-only for MVP, payment processing in Phase 3
- **Permissions:** Full RBAC + resource-level scoping (custom roles, granular permissions)

### Architecture
- **Pattern:** Modular monolith with clean extraction boundaries
- **Why not microservices:** Overkill before product-market fit, slow MVP
- **Why not classic monolith:** Module coupling risk, poor real-time support
- **Go extraction path:** Chat and notification services designed for future Go rewrite when scale demands

### Tech Stack (Python + React chosen)
- **Backend:** FastAPI + SQLModel + Pydantic v2 + Alembic
- **Frontend:** Next.js 15 + Tailwind CSS v4 + shadcn/ui + Zustand + TanStack Query
- **Database:** PostgreSQL 17 (schema-per-tenant) + Redis 7 + Meilisearch
- **Infra:** Docker + k3s on EC2 → EKS post-funding

### Why Python over Go (for this project)
- 80% business logic (booking, RBAC, multi-tenancy, pricing) — Python 2-3x faster to develop
- AI/agentic features on roadmap — Python ecosystem dominates
- Performance bottleneck won't be language — it'll be DB/network
- Go reserved for future extraction of performance-critical services

### Why SQLModel over Prisma
- Prisma's Python client is community-maintained, not official
- SQLModel built by FastAPI creator — tight integration, Pydantic-native
- Better multi-tenancy support in Python ORM ecosystem

### Generic Resource Engine (major pivot during session)
- Originally designed with 3 hardcoded domains (venues, vehicles, cooks)
- User pointed out: restaurant tables, trash vans, etc. also need to be rentable
- Pivoted to **generic resource type system** — admin defines any resource category with:
  - Custom attributes (JSONB)
  - Availability model (date_range / time_slot / hourly)
  - Pricing model selection
  - Cancellation policy
- Venues, vehicles, cooks become pre-built templates, not hardcoded domains
- Search UI auto-adapts from resource type attribute schema

### Other Key Decisions
- **Timezone:** UTC storage + local display
- **Multi-currency:** Base currency per tenant, conversion at display time
- **Cancellation:** Fully admin-configurable per resource type AND per individual resource
- **Hold duration:** Admin-configurable (default 10min)
- **Notifications:** Tenant provides own SMS/WhatsApp API keys — tenant accountable for own messaging costs
- **Tenant onboarding:** Self-service signup with onboarding wizard
- **Deployment:** k3s for lightweight K8s on single EC2, same manifests migrate to EKS

## Phasing

| Phase | Focus | Key deliverables |
|-------|-------|-----------------|
| 1 — MVP | Core platform | Multi-tenancy, resource engine, booking, RBAC, search, theming, reviews |
| 2 — Trust & Comms | Engagement | ID verification, chat, SMS/WhatsApp, calendar sync, PDF, analytics |
| 3 — Payments & Scale | Monetization | Stripe Connect, commission model, multi-currency payments, EKS migration |
| 4 — AI & Intelligence | Differentiation | Concierge agent, admin intelligence, recommendations, Go extraction, mobile apps |

## Artifacts

- **Design spec:** `docs/superpowers/specs/2026-04-28-rental-management-platform-design.md`
- **This summary:** `docs/superpowers/specs/2026-04-28-brainstorm-summary.md`

## Next Step

Create implementation plan starting from Phase 1 MVP.
