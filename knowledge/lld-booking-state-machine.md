# LLD: Booking State Machine & Concurrency

## State Diagram

```
                    ┌──────────┐
      create_booking│          │
    ───────────────►│ pending  │
    (auto_confirm   │          │
     = false)       └────┬─────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
      ┌──────────┐ ┌──────────┐ ┌──────────┐
      │confirmed │ │ rejected │ │cancelled │
      │          │ │ TERMINAL │ │ TERMINAL │
      └────┬─────┘ └──────────┘ └──────────┘
           │
      ┌────┼────────────┐
      │                 │
      ▼                 ▼
┌──────────┐      ┌──────────┐
│  active  │      │cancelled │
│          │      │ TERMINAL │
└────┬─────┘      └──────────┘
     │
     ├───────────────┬───────────────┐
     │               │               │
     ▼               ▼               ▼
┌──────────┐   ┌──────────┐   ┌──────────┐
│completed │   │cancelled │   │ no_show  │
│ TERMINAL │   │ TERMINAL │   │ TERMINAL │
└──────────┘   └──────────┘   └──────────┘
```

## Transition Table

Source: `backend/app/domains/bookings/state_machine.py`

| From | Allowed To |
|------|-----------|
| `pending` | `confirmed`, `rejected`, `cancelled` |
| `confirmed` | `active`, `cancelled` |
| `active` | `completed`, `cancelled`, `no_show` |

Terminal states (no outbound transitions): `rejected`, `completed`, `cancelled`, `no_show`

## Auto-Confirm Flow

When `BookingCreate.auto_confirm = true` (default):
1. Booking created with `status = "pending"`
2. Immediately set to `status = "confirmed"`, `confirmed_at = now`
3. Skips pending state entirely

When `auto_confirm = false`:
1. Booking stays in `pending`
2. Admin must call `POST /bookings/{id}/confirm` or `/reject`

## Concurrency Controls

### Hold System (Optimistic → Pessimistic)

Source: `backend/app/domains/resources/availability/strategy.py`

**Creating a hold** (`create_hold`):
1. `SELECT ... FOR UPDATE` on Resource row → serializes concurrent hold attempts
2. Re-check overlap under lock (prevents TOCTOU race)
3. Create `ResourceAvailability` record with `status="held"`, `hold_token`, `hold_expires`

**Confirming a hold** (`confirm_hold`):
1. `SELECT ... FOR UPDATE` on ResourceAvailability by hold_token where status="held"
2. Check hold not expired (`hold_expires < now` → delete + return false)
3. Transition: `status="booked"`, clear hold_token/hold_expires, set booking_id

**Overlap detection** (`check_overlap`):
```sql
WHERE resource_id = ?
  AND start_time < ?end
  AND end_time > ?start
  AND (status = 'booked' OR (status = 'held' AND hold_expires > now))
```

### Booking Mutations

All state transitions use `SELECT ... FOR UPDATE`:
- `confirm_booking`, `reject_booking`, `cancel_booking`, `mark_no_show`
- Prevents concurrent state changes to same booking

### Optimistic Concurrency

`Booking.version` field incremented on every state change. Not currently enforced via `WHERE version = ?` but field exists for future use.

## Cancellation Policy & Refunds

Source: `backend/app/domains/bookings/state_machine.py:calculate_refund_percent`

Cancellation policy stored as JSONB on booking (copied from ResourceType at booking time):
```json
{
  "free_cancel_hours": 48,
  "partial_cancel_hours": 24,
  "partial_refund_percent": 50,
  "no_refund_after": true
}
```

Refund calculation:
```
hours_until_start = (start_time - now) / 3600

if hours_until_start >= free_cancel_hours → 100% refund
elif hours_until_start >= partial_cancel_hours → partial_refund_percent
elif no_refund_after → 0%
else → 100% (fallback)
```

No policy (null) → always 100% refund.

## Bundled Bookings

Group related bookings (primary + addons):
- `booking_group_id` — UUID linking all bookings in a bundle
- `parent_booking_id` — FK to primary booking (null for primary)

**Cascade cancel:** Cancelling primary booking auto-cancels all addon bookings in same group with 100% refund.

**Add addon:** Only to pending/confirmed primary bookings. Cannot add addon to an addon.

## Celery Periodic Tasks

Source: `backend/app/celery_app.py`

| Task | Schedule | Action |
|------|----------|--------|
| `cleanup_expired_holds` | 60s | Delete ResourceAvailability where status="held" and hold_expires < now |
| `activate_confirmed` | 60s | Transition confirmed → active where start_time ≤ now |
| `complete_active` | 60s | Transition active → completed where end_time ≤ now |

All run per-tenant: iterate active tenants, set search_path, execute task.

## Booking Event Dispatch

On state changes, `_dispatch_booking_event` fires:
- **confirmed**: Send confirmation email (Celery), create in-app notification
- **cancelled/rejected**: Send status change email (Celery)
- **pending** (new booking): Create in-app notification for owner

Failures logged but don't block the state transition.
