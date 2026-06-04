# LLD: Reviews & Ratings

## Two-Way Review System

Source: `backend/app/domains/reviews/`

### Directions
- `customer_to_resource` — guest reviews the resource (public, affects rating)
- `lister_to_customer` — resource owner reviews the guest (stored with target_user_id)

### Review Model
```sql
reviews (
  id                UUID PK,
  booking_id        UUID FK → bookings.id,
  resource_id       UUID FK → resources.id,
  reviewer_id       UUID FK → users.id,
  target_user_id    UUID FK → users.id (null for customer→resource),
  direction         VARCHAR(20),       -- 'customer_to_resource' | 'lister_to_customer'
  rating            INT (1-5),
  category_ratings  JSONB,             -- { "cleanliness": 4, "location": 5, "value": 3 }
  title             VARCHAR(200),
  body              TEXT,
  status            VARCHAR(20),       -- 'published' | 'hidden' | 'rejected'
  moderation_reason VARCHAR(500),
  created_at        TIMESTAMPTZ,
  updated_at        TIMESTAMPTZ
)
```

## Review Creation Rules

1. **Booking must be completed** — only `status = "completed"` bookings reviewable
2. **Reviewer must be party**: 
   - `customer_to_resource`: `booking.user_id == reviewer_id`
   - `lister_to_customer`: `resource.owner_id == reviewer_id`
3. **One review per direction per booking** — 409 if duplicate

## Rating Aggregation

After each `customer_to_resource` review (create or moderation status change):

`_update_resource_rating()`:
```sql
SELECT AVG(rating), COUNT(id) FROM reviews
WHERE resource_id = ? AND direction = 'customer_to_resource' AND status = 'published'
```

Updates `resource.rating_avg` and `resource.rating_count`, then syncs to Meilisearch.

### Rating Summary Endpoint
```
GET /api/reviews/resource/{id}/summary
Response: {
  "average": 4.35,
  "count": 47,
  "distribution": { "1": 2, "2": 3, "3": 5, "4": 15, "5": 22 }
}
```

Distribution always includes keys "1" through "5" (zero-filled).

## Moderation

```
POST /api/reviews/{id}/moderate
Permission: reviews:*:moderate
Body: { status: "hidden" | "rejected" | "published", reason?: str }
```

When moderation changes published status for `customer_to_resource` reviews, rating aggregation re-runs (hidden reviews excluded from average).

## Notification Integration

On review creation → notifies resource owner:
- Event type: `review.received`
- Payload: `{ review_id, resource_name, rating }`

## Meilisearch Sync

After rating update, resource document re-synced to Meilisearch with new `rating_avg` and `rating_count`. Enables sort-by-rating in search results.
