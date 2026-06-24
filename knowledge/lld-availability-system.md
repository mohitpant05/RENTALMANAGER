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
- Frontend sends `start_time = selectedDate T00:00:00` and `end_time = endDate+1 day T00:00:00` (exclusive end boundary) to eliminate 1-minute gaps at day boundaries

### hourly
Hour-based bookings.
- Validates: start < end, duration at least 1 hour
- Check: no overlap with existing booked/held slots

### time_slot
Time-based bookings with optional fixed slots or duration constraints.

**slot_config** is set per Resource (overrides ResourceType default). Stored as JSONB on `resources.slot_config` with fallback to `resource_types.slot_config`.

```json
{
  "fixed_slots": [
    { "start": "09:00", "end": "12:00" },
    { "start": "14:00", "end": "17:00" }
  ],
  "duration_options": ["30m", "1h", "2h"]
}
```

- **fixed_slots**: When present, booking start/end must exactly match one of the defined windows. Customer sees slot picker buttons instead of time inputs.
- **duration_options**: Fallback when no fixed_slots. Constrains allowed booking durations.
- **Neither set**: Free-form time selection with basic validation (start < end, min 30m, max 12h).
- Validates: start/end must match a defined slot (if fixed_slots set), or duration must match allowed options
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

## Hold Configuration

Hold behavior is configured per `ResourceType` via `hold_config` (JSONB, nullable):

```json
{ "unit": "minutes", "value": 10 }
{ "unit": "seconds", "value": 300 }
```

- **`hold_config = null`** → No hold step. Booking goes directly to availability check + atomic insert. No countdown timer.
- **`hold_config` set** → Standard hold flow (create_hold → countdown → confirm_hold). Duration from config.
- `unit`: `"seconds"` or `"minutes"`
- `value`: 1–60 for minutes, 1–3600 for seconds

Frontend adapts UI: when hold disabled, shows "Check & Book" / "Book Now" instead of hold/countdown flow.

Managed via Resource Type settings (admin create-type-sheet).
