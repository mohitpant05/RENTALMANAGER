# LLD: Addon Discovery & Resource Templates

## Addon Discovery

Source: `backend/app/domains/resources/discovery.py`

### Concept
Resources have roles: `standalone`, `primary`, `addon`. Primary resources (venues) can have addon resources (cooks, vehicles) discovered for bundled booking.

### Discovery Algorithm

`GET /api/resources/{venue_id}/addons?start_date=&end_date=`

```
1. Load venue resource
2. Get all addon ResourceTypes (role="addon", is_active=true)
3. For each addon type:
   a. Get assigned addons (ResourceAssignment table, priority-ordered)
      - Check each assigned addon: active status + availability for dates
      - Calculate haversine distance from venue
   b. Get proximity addons (if type has discovery_radius_km > 0)
      - Load all active resources of this type with lat/lng
      - Filter by haversine distance ≤ discovery_radius_km
      - Exclude already-assigned addons
      - Check availability for each
      - Sort by distance
   c. Return: assigned first, then proximity-discovered (sorted by distance)
```

### Haversine Distance
```python
R = 6371.0 km (Earth radius)
a = sin²(Δlat/2) + cos(lat1) × cos(lat2) × sin²(Δlng/2)
distance = R × 2 × atan2(√a, √(1-a))
```

### ResourceAssignment Model
```sql
resource_assignments (
  id                    UUID PK,
  primary_resource_id   UUID FK → resources.id,  -- venue
  addon_resource_id     UUID FK → resources.id,  -- cook, vehicle
  priority              INT,                      -- sort order
  assigned_by           UUID FK → users.id,
  created_at, updated_at TIMESTAMPTZ
)
```

Admin assigns addon resources to primary resources via:
```
POST /api/resources/{id}/assignments
{ addon_resource_id: UUID, priority: int }
```

### Response Format
```json
{
  "cooks": {
    "type_name": "Cooks",
    "type_slug": "cooks",
    "resources": [
      {
        "id": "...",
        "name": "Chef Marco",
        "base_price": 50.0,
        "distance_km": 2.3,
        "is_assigned": true,
        "available": true,
        "attributes": { "cuisine_type": ["italian", "french"] }
      },
      {
        "id": "...",
        "name": "Chef Priya",
        "distance_km": 4.7,
        "is_assigned": false,
        "available": true
      }
    ]
  }
}
```

---

## Resource Type Templates

Source: `backend/app/domains/resources/templates.py`

Pre-built configurations for common resource types:

### venues
- Availability: `date_range` (full days)
- Pricing: `fixed_per_day`
- Attributes: property_type (enum), bedrooms, bathrooms, max_guests, amenities (tags), pet_friendly
- Cancellation: 48h free, 24h 50% refund, then no refund

### vehicles
- Availability: `hourly`
- Pricing: `per_hour`
- Attributes: vehicle_type (enum), vehicle_number, engine_number, chassis_number, year, seats, fuel_type (enum), transmission (enum), features (tags)
- Cancellation: 4h free, then no refund

### cooks
- Availability: `time_slot`
- Pricing: `fixed_per_slot`
- Slot config: duration options (1h, 1.5h, 2h, 3h), 30min buffer between
- Attributes: cuisine_type (tags), experience_years, specialties (tags), max_guests_served, brings_own_ingredients
- Cancellation: 24h free, 12h 50%, then no refund

### Template Usage
```
POST /api/resource-types/from-template/venues
```
Creates ResourceType with all template fields pre-filled.

## Attribute Schema Format

Each attribute in `attribute_schema` JSONB:
```json
{
  "name": "bedrooms",
  "type": "number",          // number | text | enum | boolean | tags
  "required": true,
  "filterable": true,        // added to Meilisearch filterable attributes
  "options": ["a", "b"]     // only for enum type
}
```

Attributes stored as flat JSONB on `resources.attributes`, prefixed with `attr_` in Meilisearch documents.

---

## Notification Events Registry

Source: `backend/app/core/notifications/events.py`

| Event Type | When Fired | Payload |
|-----------|-----------|---------|
| `booking.new` | New booking created (pending) | booking_id, resource_name, user_name |
| `booking.confirmed` | Booking confirmed | booking_id, resource_name |
| `booking.cancelled` | Booking cancelled | booking_id, resource_name, reason |
| `booking.rejected` | Booking rejected | booking_id, resource_name |
| `booking.completed` | Booking completed | (defined, not yet dispatched) |
| `review.received` | New review submitted | review_id, resource_name, rating |
| `review.moderated` | Review moderated | (defined, not yet dispatched) |
| `resource.approved` | Resource approved | (defined, not yet dispatched) |

Notifications stored in `notifications` table (per-tenant). Payload as JSONB.

---

## Superadmin IP Middleware

Source: `backend/app/core/admin/ip_middleware.py`

- Only applies to `/api/platform/*` paths
- If `ALLOWED_SUPERADMIN_IPS` is empty → all IPs allowed (dev mode)
- Parses comma-separated CIDR notation: `10.0.0.0/8,192.168.1.100/32`
- Non-matching IPs get `404` (not 403 — stealth denial)
- Uses Python `ipaddress` module for network matching
