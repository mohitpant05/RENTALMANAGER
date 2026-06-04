# LLD: Availability System

## Architecture

Strategy pattern with three providers, selected by `ResourceType.availability_model`.

Source: `backend/app/domains/resources/availability/`

## Provider Protocol

```python
class AvailabilityProvider(Protocol):
    def validate_times(self, start, end, slot_config) -> list[str]
    async def check(self, session, resource_id, start, end) -> bool
    async def hold(self, session, resource_id, start, end, hold_minutes=10) -> HoldResult
```

## Provider Types

### date_range
Full-day bookings. Duration in days.
- Validates: start < end
- Check: no overlap with existing booked/held slots

### hourly
Hour-based bookings.
- Validates: start < end, duration at least 1 hour
- Check: no overlap with existing booked/held slots

### time_slot
Fixed time slots defined in `ResourceType.slot_config`.
```json
{
  "slots": [
    { "start": "09:00", "end": "12:00", "label": "Morning" },
    { "start": "14:00", "end": "17:00", "label": "Afternoon" }
  ]
}
```
- Validates: start/end must match a defined slot
- Check: slot not already booked/held for that date

## ResourceAvailability Record

```sql
resource_availability (
  id             UUID PK,
  resource_id    UUID FK → resources.id,
  start_time     TIMESTAMPTZ,
  end_time       TIMESTAMPTZ,
  status         VARCHAR(20),       -- 'held' | 'booked'
  hold_token     VARCHAR(100),      -- UUID, cleared when confirmed
  hold_expires   TIMESTAMPTZ,       -- null when booked
  booking_id     UUID,              -- set when confirmed
  version        INT,
  created_at     TIMESTAMPTZ
)
```

## Hold Lifecycle

```
[Available] ─── create_hold() ──► [Held] ──── confirm_hold() ──► [Booked]
                                     │
                                     ├── release_hold() ──► [Deleted]
                                     │
                                     └── hold_expires < now ──► [Expired → Deleted by cleanup task]
```

### create_hold() — Pessimistic Locking
```
1. SELECT resource FOR UPDATE              ← serialize concurrent holds
2. check_overlap(resource_id, start, end)  ← re-verify under lock
3. If overlap → ValueError("Resource no longer available")
4. Generate hold_token = uuid4()
5. Set hold_expires = now + hold_minutes
6. INSERT ResourceAvailability(status="held")
7. COMMIT
8. Return HoldResult(hold_token, expires)
```

### confirm_hold() — Pessimistic Locking
```
1. SELECT ResourceAvailability FOR UPDATE WHERE hold_token=? AND status='held'
2. If not found → return False
3. If hold_expires < now → DELETE record, COMMIT, return False
4. UPDATE: status='booked', booking_id=?, clear hold_token & hold_expires
5. COMMIT
6. Return True
```

### Overlap Check
```sql
SELECT * FROM resource_availability
WHERE resource_id = ?
  AND start_time < ?end
  AND end_time > ?start
  AND (
    status = 'booked'
    OR (status = 'held' AND hold_expires > now())
  )
```
Returns True (available) if no rows match.

## Race Condition Prevention

1. **TOCTOU on hold**: `SELECT ... FOR UPDATE` on Resource row serializes concurrent hold attempts for same resource
2. **TOCTOU on confirm**: `SELECT ... FOR UPDATE` on ResourceAvailability record prevents double-confirm
3. **Expired hold cleanup**: Celery beat task every 60s deletes expired holds, freeing availability
4. **Hold expiry check**: `confirm_hold` checks `hold_expires` even if record exists — race between expiry cleanup and user confirmation handled

## Default Hold Duration

10 minutes (configurable via `HoldRequest.hold_minutes`).
