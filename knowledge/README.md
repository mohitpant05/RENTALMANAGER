# RentManager — System Knowledge Base

Reference documentation for agents and developers. Each file covers one system layer.

## High-Level Design (HLD)

| File | Covers |
|------|--------|
| [architecture-overview.md](architecture-overview.md) | System architecture, service map, tech stack |
| [backend.md](backend.md) | FastAPI app structure, modules, DB, multi-tenancy |
| [frontend.md](frontend.md) | Next.js structure, state management, API layer |
| [deployment.md](deployment.md) | Docker Compose (dev/prod), CI/CD pipelines |
| [kubernetes.md](kubernetes.md) | K8s/k3s manifests, networking, ingress, network policies |
| [tenant-resolution.md](tenant-resolution.md) | Tenant ID resolution from HTTP requests end-to-end |
| [data-model.md](data-model.md) | Database schema, multi-tenant isolation, migrations |

## Low-Level Design (LLD)

| File | Covers |
|------|--------|
| [lld-api-contracts.md](lld-api-contracts.md) | All API endpoints — request/response schemas, status codes, auth requirements |
| [lld-auth-flow.md](lld-auth-flow.md) | JWT structure, auth sequence diagrams (register/login/refresh/invite), RBAC permission matching |
| [lld-booking-state-machine.md](lld-booking-state-machine.md) | Booking state transitions, concurrency controls (locks, holds), cancellation policy, bundled bookings |
| [lld-availability-system.md](lld-availability-system.md) | Availability providers (date_range/hourly/time_slot), hold lifecycle, race condition prevention |
| [lld-pricing-commission.md](lld-pricing-commission.md) | Pricing models (per_day/per_hour/per_slot/tiered), commission calculation, breakdown formula |
| [lld-search-indexing.md](lld-search-indexing.md) | Meilisearch integration — index structure, document schema, filter building, geo search, sync strategy |
| [lld-payment-integration.md](lld-payment-integration.md) | Payment provider pattern (Manual/Stripe/Razorpay), payment state machine, refund flow |
| [lld-celery-tasks.md](lld-celery-tasks.md) | Background tasks — scheduling, multi-tenant execution, email retry, DB isolation per worker |
| [lld-payout-system.md](lld-payout-system.md) | Owner payout tracking — balance calculation, unsettled bookings, settle flow, money flow |
| [lld-reviews-ratings.md](lld-reviews-ratings.md) | Two-way reviews, category ratings, moderation, rating aggregation, Meilisearch sync |
| [lld-storage-email-currency.md](lld-storage-email-currency.md) | MinIO presigned upload/download, email providers (console/gmail/mandrill), currency exchange rates |
| [lld-addon-discovery.md](lld-addon-discovery.md) | Addon discovery (haversine + assignments), resource templates, notification events, superadmin IP middleware |
