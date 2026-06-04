# LLD: Meilisearch Integration

## Index Naming

Source: `backend/app/core/search/client.py`

```
Index UID: {tenant_id}_{resource_type_slug}
```
Each tenant × resource type gets own index. Full isolation.

## Index Configuration

Source: `backend/app/core/search/indexing.py`

When ResourceType created:
```python
filterable = ["status", "base_price", "rating_avg", "type_slug", "_geo"]
sortable   = ["base_price", "rating_avg", "created_at", "_geo"]
searchable = ["name", "description", "location_address"]
```

Dynamic attributes from `attribute_schema`:
- All attributes added as searchable (`attr_<name>`)
- Attributes with `filterable: true` added to filterable list

## Document Structure

Source: `backend/app/core/search/sync.py:build_document`

```json
{
  "id": "resource-uuid",
  "name": "Beach House",
  "description": "Oceanfront property...",
  "location_address": "123 Beach Rd",
  "base_price": 150.0,
  "currency": "USD",
  "status": "active",
  "rating_avg": 4.5,
  "rating_count": 23,
  "type_slug": "vacation-rental",
  "created_at": 1717500000,
  "_geo": { "lat": 34.0195, "lng": -118.4912 },
  "attr_bedrooms": 3,
  "attr_pool": true,
  "attr_pet_friendly": "yes"
}
```
- `_geo` only set when both lat+lng present
- Resource attributes flattened with `attr_` prefix
- `created_at` stored as Unix timestamp for sorting

## Sync Strategy

### Real-time sync
On resource CRUD (`backend/app/domains/resources/service.py`):
- Create/Update → `sync_resource(tenant_id, type_slug, document)`
- Delete → `remove_resource(tenant_id, type_slug, resource_id)`

### Full reindex (Celery beat, nightly)
Task: `search.full_reindex` — schedule: 86400s (24h)

For each active tenant:
1. Set search_path to tenant schema
2. Load all resource types + resources
3. Rebuild all documents
4. Upsert into Meilisearch indexes

## Search Query Execution

Source: `backend/app/core/search/query.py`

### Filter Building
```python
# Always applied:
['status = "active"']

# User filters (dict):
{ "bedrooms": 3 }           → 'attr_bedrooms = "3"'
{ "bedrooms": [2, 3] }      → '(attr_bedrooms = "2" OR attr_bedrooms = "3")'
{ "base_price": {"min": 50, "max": 200} } → 'base_price >= 50', 'base_price <= 200'

# Geo filter:
geo_lat + geo_lng + geo_radius_km → '_geoRadius(lat, lng, radius_in_meters)'
```

Known keys (`status`, `base_price`, `rating`) not prefixed with `attr_`.

### Sort
```
sort_by = "base_price"  → ["base_price:asc"]
sort_by = "_geo"        → ["_geoPoint(lat, lng):asc"]
sort_by = "bedrooms"    → ["attr_bedrooms:asc"]
```

### Cross-type Search
When no `resource_type_slug` provided:
1. Query all active primary/standalone ResourceTypes
2. Search each index separately
3. Merge hits, re-sort by requested field
4. Apply offset/limit to merged results

## Geo Search

Meilisearch native geo support:
- **Filter**: `_geoRadius(lat, lng, radius_m)` — only return within radius
- **Sort**: `_geoPoint(lat, lng):asc` — sort by distance
- Both can be combined

Geo configured per index when resource type created (`configure_geo`).
