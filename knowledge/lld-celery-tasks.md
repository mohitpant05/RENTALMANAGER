# LLD: Celery Background Tasks

## Configuration

Source: `backend/app/celery_app.py`

- Broker: Redis
- Backend: Redis
- Serializer: JSON
- Task acks: late (at-least-once delivery)
- Prefetch multiplier: 1 (fair scheduling)

## Per-Worker Database Isolation

Each Celery task creates a fresh SQLAlchemy engine + session factory per invocation (`_make_task_session_factory`). Prevents asyncpg connection pool sharing across forked workers.

Pool size: 5 + 2 overflow per task.

## Multi-Tenant Task Execution

`_run_for_all_tenants(task_fn)`:
1. Load all active tenants from public schema
2. For each tenant: `SET search_path TO <schema>, public`
3. Execute task function
4. `SET search_path TO public`
5. Dispose engine when done

## Scheduled Tasks (Celery Beat)

| Task Name | Schedule | Function | Description |
|-----------|----------|----------|-------------|
| `bookings.cleanup_expired_holds` | 60s | `cleanup_expired_holds` | Delete ResourceAvailability where held + expired |
| `bookings.activate_confirmed` | 60s | `activate_confirmed_bookings` | confirmed → active where start_time ≤ now |
| `bookings.complete_active` | 60s | `complete_active_bookings` | active → completed where end_time ≤ now |
| `search.full_reindex` | 86400s (24h) | `full_reindex` | Rebuild all Meilisearch indexes per tenant |
| `currency.refresh_rates` | 43200s (12h) | `refresh_rates_cache` | Update exchange rate cache |

## On-Demand Tasks

### email.send
```python
@celery.task(name="email.send", bind=True, max_retries=3, queue="email")
def task_send_email(self, to, subject, body):
```
- Separate `email` queue
- Retry: 3 attempts, exponential backoff (30s, 60s, 120s)
- Provider from factory: console (dev), Gmail SMTP, Mandrill

Triggered by:
- User registration (welcome email)
- Staff invite (invite link email)
- Booking confirmed (confirmation email)
- Booking cancelled/rejected (status change email)

## Task Error Handling

- Email tasks: retry with backoff, log on final failure
- Booking lifecycle tasks: per-tenant, skip on failure (other tenants still processed)
- Search reindex: per-tenant, skip on failure
- All tasks: fresh DB engine per invocation (no stale connection issues)

## Deployment

- `celery-worker`: `celery -A app.celery_app worker --loglevel=info`
- `celery-beat`: `celery -A app.celery_app beat --loglevel=info`
- Both share same Docker image as backend
- K8s: separate Deployments, 1 replica each
