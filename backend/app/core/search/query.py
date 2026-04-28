from app.core.search.client import get_index_uid, get_meili_client
from app.core.search.schemas import SearchHit, SearchRequest, SearchResponse


def _build_filter_string(filters: dict | None) -> list[str]:
    if not filters:
        return []
    parts = []
    for key, value in filters.items():
        if key.startswith(("status", "base_price", "rating")):
            attr_key = key
        else:
            attr_key = f"attr_{key}"
        if isinstance(value, list):
            conditions = [f'{attr_key} = "{v}"' for v in value]
            parts.append(f"({' OR '.join(conditions)})")
        elif isinstance(value, dict):
            if "min" in value:
                parts.append(f"{attr_key} >= {value['min']}")
            if "max" in value:
                parts.append(f"{attr_key} <= {value['max']}")
        else:
            parts.append(f'{attr_key} = "{value}"')
    return parts


def execute_search(tenant_id: str, request: SearchRequest) -> SearchResponse:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, request.resource_type_slug)
    index = client.index(uid)

    search_params: dict = {
        "offset": request.offset,
        "limit": request.limit,
    }

    filter_parts = ['status = "active"']
    filter_parts.extend(_build_filter_string(request.filters))

    if (
        request.geo_lat is not None
        and request.geo_lng is not None
        and request.geo_radius_km
    ):
        radius_m = int(request.geo_radius_km * 1000)
        filter_parts.append(
            f"_geoRadius({request.geo_lat}, {request.geo_lng}, {radius_m})"
        )

    search_params["filter"] = filter_parts

    if request.sort_by:
        sort_attr = request.sort_by
        if not sort_attr.startswith(("base_price", "rating_avg", "created_at", "_geo")):
            sort_attr = f"attr_{sort_attr}"
        if (
            sort_attr == "_geo"
            and request.geo_lat is not None
            and request.geo_lng is not None
        ):
            search_params["sort"] = [
                f"_geoPoint({request.geo_lat}, {request.geo_lng}):{request.sort_order}"
            ]
        else:
            search_params["sort"] = [f"{sort_attr}:{request.sort_order}"]

    result = index.search(request.q, search_params)

    hits = []
    for hit in result["hits"]:
        attrs = {}
        geo = hit.get("_geo")
        for k, v in hit.items():
            if k.startswith("attr_"):
                attrs[k[5:]] = v
        hits.append(SearchHit(
            id=hit["id"],
            name=hit.get("name", ""),
            description=hit.get("description", ""),
            location_address=hit.get("location_address", ""),
            base_price=hit.get("base_price", 0),
            currency=hit.get("currency", "USD"),
            status=hit.get("status", ""),
            rating_avg=hit.get("rating_avg", 0),
            rating_count=hit.get("rating_count", 0),
            type_slug=hit.get("type_slug", ""),
            geo=geo,
            attributes=attrs if attrs else None,
        ))

    return SearchResponse(
        hits=hits,
        query=result.get("query", request.q),
        processing_time_ms=result.get("processingTimeMs", 0),
        estimated_total_hits=result.get("estimatedTotalHits", 0),
        offset=request.offset,
        limit=request.limit,
    )
