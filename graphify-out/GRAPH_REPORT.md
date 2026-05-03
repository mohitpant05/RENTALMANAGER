# Graph Report - .  (2026-04-30)

## Corpus Check
- 164 files · ~84,995 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1036 nodes · 1570 edges · 59 communities detected
- Extraction: 64% EXTRACTED · 36% INFERRED · 0% AMBIGUOUS · INFERRED: 558 edges (avg confidence: 0.79)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Resource Availability & Validation|Resource Availability & Validation]]
- [[_COMMUNITY_API Router & Service Layer|API Router & Service Layer]]
- [[_COMMUNITY_Pydantic Schema Definitions|Pydantic Schema Definitions]]
- [[_COMMUNITY_Booking Engine & Admin API|Booking Engine & Admin API]]
- [[_COMMUNITY_Auth & JWT Configuration|Auth & JWT Configuration]]
- [[_COMMUNITY_Storage & App Entry|Storage & App Entry]]
- [[_COMMUNITY_Infrastructure & Tenancy|Infrastructure & Tenancy]]
- [[_COMMUNITY_Database Models & Migrations|Database Models & Migrations]]
- [[_COMMUNITY_Notifications System|Notifications System]]
- [[_COMMUNITY_Search & Indexing|Search & Indexing]]
- [[_COMMUNITY_Domain Logic Patterns|Domain Logic Patterns]]
- [[_COMMUNITY_Architecture Documentation|Architecture Documentation]]
- [[_COMMUNITY_Auth & Admin Services|Auth & Admin Services]]
- [[_COMMUNITY_Frontend Auth & API Layer|Frontend Auth & API Layer]]
- [[_COMMUNITY_Email Provider System|Email Provider System]]
- [[_COMMUNITY_Admin Integration Tests|Admin Integration Tests]]
- [[_COMMUNITY_Reviews CRUD|Reviews CRUD]]
- [[_COMMUNITY_Strategy Pattern Protocols|Strategy Pattern Protocols]]
- [[_COMMUNITY_Event-Driven Notifications|Event-Driven Notifications]]
- [[_COMMUNITY_Frontend App Shell|Frontend App Shell]]
- [[_COMMUNITY_Invite Flow Tests|Invite Flow Tests]]
- [[_COMMUNITY_Implementation Plans|Implementation Plans]]
- [[_COMMUNITY_Email Dispatch Pipeline|Email Dispatch Pipeline]]
- [[_COMMUNITY_Review & Rating System|Review & Rating System]]
- [[_COMMUNITY_Migration Public Schema|Migration: Public Schema]]
- [[_COMMUNITY_Migration Auth RBAC|Migration: Auth RBAC]]
- [[_COMMUNITY_Migration Tenant Themes|Migration: Tenant Themes]]
- [[_COMMUNITY_Notification Testing|Notification Testing]]
- [[_COMMUNITY_Deployment & CICD|Deployment & CI/CD]]
- [[_COMMUNITY_Platform Admin Routing|Platform Admin Routing]]
- [[_COMMUNITY_Storage Client Tests|Storage Client Tests]]
- [[_COMMUNITY_Component Group 61|Component Group 61]]
- [[_COMMUNITY_Component Group 62|Component Group 62]]
- [[_COMMUNITY_Component Group 63|Component Group 63]]
- [[_COMMUNITY_Component Group 90|Component Group 90]]
- [[_COMMUNITY_Component Group 91|Component Group 91]]
- [[_COMMUNITY_Component Group 92|Component Group 92]]
- [[_COMMUNITY_Component Group 93|Component Group 93]]
- [[_COMMUNITY_Component Group 94|Component Group 94]]
- [[_COMMUNITY_Component Group 95|Component Group 95]]
- [[_COMMUNITY_Component Group 96|Component Group 96]]
- [[_COMMUNITY_Component Group 97|Component Group 97]]
- [[_COMMUNITY_Component Group 98|Component Group 98]]
- [[_COMMUNITY_Component Group 99|Component Group 99]]
- [[_COMMUNITY_Component Group 100|Component Group 100]]
- [[_COMMUNITY_Component Group 101|Component Group 101]]
- [[_COMMUNITY_Component Group 102|Component Group 102]]
- [[_COMMUNITY_Component Group 103|Component Group 103]]
- [[_COMMUNITY_Component Group 104|Component Group 104]]
- [[_COMMUNITY_Component Group 105|Component Group 105]]
- [[_COMMUNITY_Component Group 106|Component Group 106]]
- [[_COMMUNITY_Component Group 107|Component Group 107]]
- [[_COMMUNITY_Component Group 108|Component Group 108]]
- [[_COMMUNITY_Component Group 109|Component Group 109]]
- [[_COMMUNITY_Component Group 110|Component Group 110]]
- [[_COMMUNITY_Component Group 111|Component Group 111]]
- [[_COMMUNITY_Component Group 112|Component Group 112]]
- [[_COMMUNITY_Component Group 113|Component Group 113]]
- [[_COMMUNITY_Component Group 114|Component Group 114]]

## God Nodes (most connected - your core abstractions)
1. `refresh()` - 34 edges
2. `get_current_tenant()` - 26 edges
3. `get_settings()` - 16 edges
4. `can_transition()` - 16 edges
5. `validate_attributes()` - 16 edges
6. `test_tenant()` - 14 edges
7. `get_redis()` - 12 edges
8. `get_pricing_provider()` - 11 edges
9. `AvailabilityProvider` - 10 edges
10. `get_availability_provider()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `SQLAlchemy async engine, session factory, tenant-aware get_db` --semantically_similar_to--> `Zustand tenant store (slug persisted in localStorage)`  [INFERRED] [semantically similar]
  backend/app/database.py → frontend/src/lib/tenant-store.ts
- `Zustand auth store (accessToken, user, refresh token in localStorage)` --jwt_tokens_created_by_backend_consumed_by_frontend--> `Settings`  [INFERRED]
  frontend/src/lib/auth-store.ts → /Users/mohit.pant/PERSONAL/RM/backend/app/config.py
- `Architecture pattern: PostgreSQL schema-per-tenant isolation` --schema_name_column_implements--> `tenants table: id, name, slug, schema_name, is_active, config JSONB, base_currency, timezone`  [EXTRACTED]
  docs/superpowers/specs/2026-04-28-rental-management-platform-design.md → backend/alembic/versions/0001_public_schema.py
- `White-label theming: JSONB-stored brand/colors/typography/components/features` --stored_in--> `tenant_themes table: JSONB columns for white-label theming, FK to tenants`  [EXTRACTED]
  docs/superpowers/plans/2026-04-28-09-admin-panel.md → backend/alembic/versions/0003_tenant_themes.py
- `Redis async client factory (lru_cache singleton)` --reads_redis_url--> `Settings`  [EXTRACTED]
  backend/app/redis_client.py → /Users/mohit.pant/PERSONAL/RM/backend/app/config.py

## Hyperedges (group relationships)
- **Tenant Resolution Flow** — middleware_tenant_resolution, tenant_initializer_component, tenant_store_ref [INFERRED 0.90]
- **Authentication Lifecycle** — use_auth_hook, api_client_ref, auth_store_ref, api_token_response, api_user_response [EXTRACTED 1.00]
- **App Shell Layout** — icon_rail_component, sub_nav_component, header_component [INFERRED 0.85]
- **Frontend API Layer** — api_axios_client, auth_store_zustand, tenant_store_zustand, token_refresh_flow [EXTRACTED 1.00]
- **Backend Infrastructure Services** — config_settings, database_module, redis_client_module, celery_app_module [EXTRACTED 1.00]
- **Frontend Auth Flow** — login_page, accept_invite_page, admin_layout_component, use_auth_hook, auth_store_zustand [EXTRACTED 1.00]
- **** — tenant_middleware, tenant_context, auth_dependencies, auth_router [INFERRED 0.90]
- **** — admin_service, auth_invite, auth_service [EXTRACTED 1.00]
- **** — auth_seed, role_model, permission_model, role_permission_model, tenant_provisioning [EXTRACTED 1.00]
- **Full Reindex Pipeline** — search_tasks, search_sync, search_indexing, meili_client, resource_model, resource_type_model [EXTRACTED 1.00]
- **File Upload Lifecycle** — storage_router, storage_service, minio_client, attachment_model [EXTRACTED 1.00]
- **Search Execution Pipeline** — search_router, search_query, meili_client, search_schemas [EXTRACTED 1.00]
- **Booking Creation Flow** — service_bookings, state_machine_bookings, model_booking, model_resource, model_resource_type [EXTRACTED 1.00]
- **Email Strategy Pattern** — factory_email, gmail_provider, mandrill_provider, provider_email_abc [EXTRACTED 1.00]
- **Scheduled Lifecycle Maintenance** — tasks_bookings, model_booking, model_resource_availability [EXTRACTED 1.00]
- **Availability Strategy Dispatch** — availability_provider_protocol, date_range_provider, hourly_provider, time_slot_provider, get_availability_provider [EXTRACTED 1.00]
- **Pricing Strategy Dispatch** — pricing_provider_protocol, fixed_per_day_provider, fixed_per_slot_provider, hourly_pricing_provider, tiered_provider, get_pricing_provider [EXTRACTED 1.00]
- **Review Rating Sync Flow** — create_review_fn, update_resource_rating_fn, moderate_review_fn [EXTRACTED 1.00]
- **** — conftest_db_engine, conftest_db_session, conftest_test_tenant, conftest_admin_headers, conftest_customer_headers, conftest_client [EXTRACTED 1.00]
- **** — test_booking_integration, test_resource_integration, test_review_integration [INFERRED 0.80]
- **** — email_factory, gmail_provider, mandrill_provider, task_send_email [EXTRACTED 1.00]
- **Multi-tenant data isolation: schema-per-tenant + ContextVar propagation + search_path switching + per-tenant buckets + per-tenant search indexes** — concept_schema_per_tenant, concept_context_var_tenant, concept_dependency_injection_fastapi, concept_presigned_urls, concept_meilisearch_per_tenant_index [INFERRED 0.90]
- **Resource lifecycle: generic engine defines resources -> availability/pricing strategies -> bookings consume -> reviews evaluate -> search indexes** — concept_generic_resource_engine, concept_strategy_pattern_availability, concept_strategy_pattern_pricing, concept_booking_state_machine, concept_two_way_reviews, concept_meilisearch_per_tenant_index [INFERRED 0.85]
- **Invite auth pipeline: admin invites -> email provider sends -> Redis stores token -> user accepts -> JWT issued -> RBAC roles assigned** — concept_invite_only_auth, concept_email_provider_abc, concept_jwt_redis_refresh, concept_rbac_wildcard_permissions, concept_celery_background_tasks [EXTRACTED 0.95]

## Communities

### Community 0 - "Resource Availability & Validation"
Cohesion: 0.04
Nodes (54): _check_type(), validate_attributes(), DateRangeProvider, HourlyProvider, Resource, ResourceAvailability, ResourceType, ResourceTypeCreate Pydantic schema (+46 more)

### Community 1 - "API Router & Service Layer"
Cohesion: 0.05
Nodes (62): get_current_tenant(), Protocol, FixedPerDayProvider, FixedPerSlotProvider, HourlyPricingProvider, TieredProvider, add_tenant_domain(), calculate_price() (+54 more)

### Community 2 - "Pydantic Schema Definitions"
Cohesion: 0.04
Nodes (57): BaseModel, Review, AcceptInviteRequest, AvailabilityCheckRequest, BookingCancel, BookingCreate, BookingReject, BookingResponse (+49 more)

### Community 3 - "Booking Engine & Admin API"
Cohesion: 0.04
Nodes (48): Booking, activate_tenant(), deactivate_tenant(), cancel_booking_endpoint(), confirm_booking_endpoint(), create_booking_endpoint(), get_booking_endpoint(), list_bookings_endpoint() (+40 more)

### Community 4 - "Auth & JWT Configuration"
Cohesion: 0.05
Nodes (55): BaseSettings, Celery app with beat schedule (booking tasks, search reindex, email), get_settings(), Settings, SQLAlchemy async engine, session factory, tenant-aware get_db, get_current_user(), matches_permission(), require_permission() (+47 more)

### Community 5 - "Storage & App Entry"
Cohesion: 0.07
Nodes (36): ensure_bucket(), get_minio_client(), get_tenant_bucket(), health_all(), health_meilisearch(), health_minio(), health_postgres(), health_redis() (+28 more)

### Community 6 - "Infrastructure & Tenancy"
Cohesion: 0.07
Nodes (25): BaseHTTPMiddleware, _run_async(), _run_for_all_tenants(), task_activate_confirmed(), task_cleanup_expired_holds(), task_complete_active(), task_full_reindex(), admin_headers() (+17 more)

### Community 7 - "Database Models & Migrations"
Cohesion: 0.07
Nodes (27): run_async_migrations(), run_migrations_online(), Permission, PlatformConfig, Role, RolePermission, TenantDomain, TenantTheme (+19 more)

### Community 8 - "Notifications System"
Cohesion: 0.06
Nodes (26): booking_confirmed_payload(), booking_new_payload(), review_received_payload(), Notification, get_my_unread_count(), list_my_notifications(), mark_all_notifications_read(), mark_notification_read() (+18 more)

### Community 9 - "Search & Indexing"
Cohesion: 0.09
Nodes (29): get_index_uid(), get_meili_client(), configure_geo(), create_resource_type_index(), delete_resource_type_index(), _build_filter_string(), execute_search(), search_resources() (+21 more)

### Community 10 - "Domain Logic Patterns"
Cohesion: 0.08
Nodes (24): Attachment Model, Resource Attribute Validation, Availability Strategy Pattern, Booking State Machine, Cancellation/Refund Policy, cleanup_expired_holds task, Meilisearch Client, MinIO Client (+16 more)

### Community 11 - "Architecture Documentation"
Cohesion: 0.08
Nodes (30): Alembic async migration runner with SQLModel metadata registration, ASGI onion middleware model vs Express linear middleware, Booking state machine: PENDING->CONFIRMED->ACTIVE->COMPLETED (+REJECTED/CANCELLED/NO_SHOW), Cancellation refund calculator: free_cancel_hours, partial windows, refund percentages, Celery tasks: booking lifecycle, hold cleanup, search reindex, email delivery, Pattern: ContextVar for async-safe tenant context propagation, FastAPI Depends() as per-route dependency injection with yield cleanup, Email provider interface: ABC with Gmail SMTP and Mandrill implementations (+22 more)

### Community 12 - "Auth & Admin Services"
Cohesion: 0.12
Nodes (27): Admin Pydantic Schemas (theme, tenant, domain, staff), Admin Service (theme, config, domains, staff invite), Auth Dependencies (get_current_user, require_permission), Invite Token Management (Redis-backed), JWT Token Management (create, decode, revoke), Auth Router (/api/auth endpoints), Auth Pydantic Schemas, RBAC Seed (default roles and permissions) (+19 more)

### Community 13 - "Frontend Auth & API Layer"
Cohesion: 0.08
Nodes (28): Accept invite page (verify token, set password), Admin layout (auth guard, IconRail + SubNav + Header shell), AcceptInviteRequest interface (token + password), Axios API client with interceptors (request auth, token refresh), api client (external ref: @/lib/api), LoginRequest interface, TenantResponse interface (tenant config, currency, timezone), ThemeResponse interface (brand, colors, typography, components, features) (+20 more)

### Community 14 - "Email Provider System"
Cohesion: 0.13
Nodes (14): ABC, task_send_email(), EmailProvider, get_email_provider(), GmailSMTPProvider, MandrillProvider, EmailProvider, test_factory_returns_gmail_provider() (+6 more)

### Community 16 - "Admin Integration Tests"
Cohesion: 0.13
Nodes (3): PlatformUser, platform_headers(), test_platform_login()

### Community 18 - "Reviews CRUD"
Cohesion: 0.23
Nodes (13): create_lister_review(), create_resource_review(), get_one_review(), get_rating_summary(), list_all_reviews(), list_my_reviews(), moderate_one_review(), create_review() (+5 more)

### Community 19 - "Strategy Pattern Protocols"
Cohesion: 0.26
Nodes (15): AvailabilityProvider Protocol, check_overlap() function, confirm_hold() function, create_hold() function, DateRangeProvider class, FixedPerDayProvider class, FixedPerSlotProvider class, get_availability_provider() factory (+7 more)

### Community 20 - "Event-Driven Notifications"
Cohesion: 0.27
Nodes (13): Notification Event Constants and Payload Builders, Booking SQLModel, Resource SQLModel, ResourceAvailability SQLModel, ResourceType SQLModel, Bookings API Router, Notifications API Router, Booking Pydantic Schemas (+5 more)

### Community 21 - "Frontend App Shell"
Cohesion: 0.2
Nodes (5): IconRail(), AdminLayout(), AcceptInvitePage(), LoginPage(), useAuth()

### Community 22 - "Invite Flow Tests"
Cohesion: 0.33
Nodes (5): _get_invite_token(), test_accept_invite_activates_user_and_returns_tokens(), test_accept_invite_token_single_use(), test_reinvite_active_user_fails(), test_verify_invite_valid_token()

### Community 24 - "Implementation Plans"
Cohesion: 0.22
Nodes (9): Plan: TenantTheme model, admin service, platform superadmin, staff management, Plan: email provider module, invite token flow, accept-invite frontend, Plan: User/Role/Permission models, JWT with Redis refresh, RBAC dependencies, Plan: booking engine with state machine, cancellation policy, hold system, Plan: Docker Compose stack, Traefik, FastAPI scaffold, Alembic setup, Plan: generic resource engine with strategy pattern for availability and pricing, Plan: two-way review system with moderation and rating aggregation, Plan: Meilisearch integration with per-tenant per-resource-type indexes (+1 more)

### Community 26 - "Email Dispatch Pipeline"
Cohesion: 0.57
Nodes (6): Email Provider Factory, Email Provider Factory, GmailSMTPProvider, MandrillProvider, EmailProvider ABC, task_send_email Celery task

### Community 29 - "Review & Rating System"
Cohesion: 0.4
Nodes (6): create_review() service function, moderate_review() service function, Review SQLModel, reviews router APIRouter, reviews service module, _update_resource_rating() helper

### Community 31 - "Migration: Public Schema"
Cohesion: 0.5
Nodes (1): create public schema tables  Revision ID: 0001 Revises: Create Date: 2026-04-28

### Community 32 - "Migration: Auth RBAC"
Cohesion: 0.5
Nodes (1): add auth and rbac tables  Revision ID: 0002 Revises: 0001 Create Date: 2026-04-2

### Community 33 - "Migration: Tenant Themes"
Cohesion: 0.5
Nodes (1): add tenant_themes table  Revision ID: 0003 Revises: 0002 Create Date: 2026-04-29

### Community 34 - "Notification Testing"
Cohesion: 0.5
Nodes (2): Notification Event Types, notify() service function

### Community 35 - "Deployment & CI/CD"
Cohesion: 0.5
Nodes (4): Docker Compose 9-service stack: postgres, redis, meilisearch, minio, backend, celery-worker, celery-beat, frontend, traefik, GitHub Actions CI (lint+test) and CD (build->ECR->kubectl deploy), k3s Kubernetes production deployment with init containers for migrations, Project setup guide: 9-service Docker Compose stack, request flow, multi-tenancy in dev

### Community 39 - "Platform Admin Routing"
Cohesion: 0.67
Nodes (2): Tenant Admin Router, Platform Admin Router

### Community 40 - "Storage Client Tests"
Cohesion: 1.0
Nodes (1): Storage Client (S3/MinIO)

### Community 61 - "Component Group 61"
Cohesion: 1.0
Nodes (2): Button component with variant/size CVA system, Sheet component (slide-over panel based on base-ui Dialog)

### Community 62 - "Component Group 62"
Cohesion: 1.0
Nodes (2): Spec: brainstorm summary with business model decisions and architecture rationale, Spec: full rental management platform design (architecture, multi-tenancy, all modules)

### Community 63 - "Component Group 63"
Cohesion: 1.0
Nodes (2): Plan: Next.js 15 frontend with Zustand, TanStack Query, shadcn/ui shell, Spec: admin dashboard frontend design (shell, auth, modules, data fetching)

### Community 90 - "Component Group 90"
Cohesion: 1.0
Nodes (1): VerifyInviteResponse interface

### Community 91 - "Component Group 91"
Cohesion: 1.0
Nodes (1): Header: breadcrumb navigation derived from pathname

### Community 92 - "Component Group 92"
Cohesion: 1.0
Nodes (1): Card component family (Card, CardHeader, CardTitle, CardContent, etc.)

### Community 93 - "Component Group 93"
Cohesion: 1.0
Nodes (1): DropdownMenu component family (base-ui Menu primitive)

### Community 94 - "Component Group 94"
Cohesion: 1.0
Nodes (1): Input component (base-ui Input primitive)

### Community 95 - "Component Group 95"
Cohesion: 1.0
Nodes (1): Label component

### Community 96 - "Component Group 96"
Cohesion: 1.0
Nodes (1): Separator component (base-ui Separator primitive)

### Community 97 - "Component Group 97"
Cohesion: 1.0
Nodes (1): Next.js root layout with Providers wrapper

### Community 98 - "Component Group 98"
Cohesion: 1.0
Nodes (1): Auth layout (split-screen branding + form)

### Community 99 - "Component Group 99"
Cohesion: 1.0
Nodes (1): Settings page (stub)

### Community 100 - "Component Group 100"
Cohesion: 1.0
Nodes (1): Bookings page (stub)

### Community 101 - "Component Group 101"
Cohesion: 1.0
Nodes (1): Theming page (stub)

### Community 102 - "Component Group 102"
Cohesion: 1.0
Nodes (1): PlatformConfig SQLModel

### Community 103 - "Component Group 103"
Cohesion: 1.0
Nodes (1): Common Mixins (UUID, Timestamp)

### Community 104 - "Component Group 104"
Cohesion: 1.0
Nodes (1): resources schemas module

### Community 105 - "Component Group 105"
Cohesion: 1.0
Nodes (1): resources router module

### Community 106 - "Component Group 106"
Cohesion: 1.0
Nodes (1): availability strategy module

### Community 107 - "Component Group 107"
Cohesion: 1.0
Nodes (1): HoldResult dataclass

### Community 108 - "Component Group 108"
Cohesion: 1.0
Nodes (1): release_hold() function

### Community 109 - "Component Group 109"
Cohesion: 1.0
Nodes (1): reviews schemas module

### Community 110 - "Component Group 110"
Cohesion: 1.0
Nodes (1): ResourceCreate Pydantic schema

### Community 111 - "Component Group 111"
Cohesion: 1.0
Nodes (1): tests/conftest.py

### Community 112 - "Component Group 112"
Cohesion: 1.0
Nodes (1): Plan: MinIO file storage with presigned URLs and per-tenant bucket isolation

### Community 113 - "Component Group 113"
Cohesion: 1.0
Nodes (1): Plan: in-app notification system with channel router pattern

### Community 114 - "Component Group 114"
Cohesion: 1.0
Nodes (1): Plan: multi-stage Docker, k3s Kubernetes, GitHub Actions CI/CD

## Knowledge Gaps
- **85 isolated node(s):** `create public schema tables  Revision ID: 0001 Revises: Create Date: 2026-04-28`, `add auth and rbac tables  Revision ID: 0002 Revises: 0001 Create Date: 2026-04-2`, `add tenant_themes table  Revision ID: 0003 Revises: 0002 Create Date: 2026-04-29`, `Next.js API proxy rewrites config`, `Edge middleware: tenant slug resolution from URL path or subdomain` (+80 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Migration: Public Schema`** (4 nodes): `downgrade()`, `create public schema tables  Revision ID: 0001 Revises: Create Date: 2026-04-28`, `upgrade()`, `0001_public_schema.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration: Auth RBAC`** (4 nodes): `downgrade()`, `add auth and rbac tables  Revision ID: 0002 Revises: 0001 Create Date: 2026-04-2`, `upgrade()`, `0002_auth_rbac.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Migration: Tenant Themes`** (4 nodes): `downgrade()`, `add tenant_themes table  Revision ID: 0003 Revises: 0002 Create Date: 2026-04-29`, `upgrade()`, `0003_tenant_themes.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Notification Testing`** (4 nodes): `Notification Event Types`, `notify() service function`, `test_notification_integration.py`, `test_notification_unit.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Platform Admin Routing`** (3 nodes): `Tenant Admin Router`, `Platform Admin Router`, `provision_tenant_schema()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Storage Client Tests`** (3 nodes): `Storage Client (S3/MinIO)`, `test_storage_integration.py`, `test_storage_unit.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 61`** (2 nodes): `Button component with variant/size CVA system`, `Sheet component (slide-over panel based on base-ui Dialog)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 62`** (2 nodes): `Spec: brainstorm summary with business model decisions and architecture rationale`, `Spec: full rental management platform design (architecture, multi-tenancy, all modules)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 63`** (2 nodes): `Plan: Next.js 15 frontend with Zustand, TanStack Query, shadcn/ui shell`, `Spec: admin dashboard frontend design (shell, auth, modules, data fetching)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 90`** (1 nodes): `VerifyInviteResponse interface`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 91`** (1 nodes): `Header: breadcrumb navigation derived from pathname`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 92`** (1 nodes): `Card component family (Card, CardHeader, CardTitle, CardContent, etc.)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 93`** (1 nodes): `DropdownMenu component family (base-ui Menu primitive)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 94`** (1 nodes): `Input component (base-ui Input primitive)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 95`** (1 nodes): `Label component`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 96`** (1 nodes): `Separator component (base-ui Separator primitive)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 97`** (1 nodes): `Next.js root layout with Providers wrapper`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 98`** (1 nodes): `Auth layout (split-screen branding + form)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 99`** (1 nodes): `Settings page (stub)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 100`** (1 nodes): `Bookings page (stub)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 101`** (1 nodes): `Theming page (stub)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 102`** (1 nodes): `PlatformConfig SQLModel`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 103`** (1 nodes): `Common Mixins (UUID, Timestamp)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 104`** (1 nodes): `resources schemas module`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 105`** (1 nodes): `resources router module`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 106`** (1 nodes): `availability strategy module`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 107`** (1 nodes): `HoldResult dataclass`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 108`** (1 nodes): `release_hold() function`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 109`** (1 nodes): `reviews schemas module`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 110`** (1 nodes): `ResourceCreate Pydantic schema`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 111`** (1 nodes): `tests/conftest.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 112`** (1 nodes): `Plan: MinIO file storage with presigned URLs and per-tenant bucket isolation`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 113`** (1 nodes): `Plan: in-app notification system with channel router pattern`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Component Group 114`** (1 nodes): `Plan: multi-stage Docker, k3s Kubernetes, GitHub Actions CI/CD`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `refresh()` connect `Booking Engine & Admin API` to `Resource Availability & Validation`, `API Router & Service Layer`, `Auth & JWT Configuration`, `Storage & App Entry`, `Infrastructure & Tenancy`, `Database Models & Migrations`, `Notifications System`, `Admin Integration Tests`, `Reviews CRUD`?**
  _High betweenness centrality (0.138) - this node is a cross-community bridge._
- **Why does `get_settings()` connect `Auth & JWT Configuration` to `Search & Indexing`, `Storage & App Entry`, `Email Provider System`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `invite_staff()` connect `Auth & JWT Configuration` to `API Router & Service Layer`, `Booking Engine & Admin API`, `Database Models & Migrations`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 33 inferred relationships involving `refresh()` (e.g. with `create_booking()` and `confirm_booking()`) actually correct?**
  _`refresh()` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `get_current_tenant()` (e.g. with `get_db()` and `create_resource_type()`) actually correct?**
  _`get_current_tenant()` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `get_settings()` (e.g. with `get_redis()` and `lifespan()`) actually correct?**
  _`get_settings()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `create public schema tables  Revision ID: 0001 Revises: Create Date: 2026-04-28`, `add auth and rbac tables  Revision ID: 0002 Revises: 0001 Create Date: 2026-04-2`, `add tenant_themes table  Revision ID: 0003 Revises: 0002 Create Date: 2026-04-29` to the rest of the system?**
  _85 weakly-connected nodes found - possible documentation gaps or missing edges._