from __future__ import annotations

import uuid
from datetime import datetime

import meilisearch

from app.core.search.client import get_index_uid, get_meili_client


def build_document(
    resource_id: uuid.UUID,
    name: str,
    description: str | None,
    location_lat: float | None,
    location_lng: float | None,
    location_address: str | None,
    attributes: dict | None,
    base_price: float,
    currency: str,
    status: str,
    rating_avg: float,
    rating_count: int,
    type_slug: str,
    created_at: datetime,
) -> dict:
    doc: dict = {
        "id": str(resource_id),
        "name": name,
        "description": description or "",
        "location_address": location_address or "",
        "base_price": base_price,
        "currency": currency,
        "status": status,
        "rating_avg": rating_avg,
        "rating_count": rating_count,
        "type_slug": type_slug,
        "created_at": int(created_at.timestamp()),
    }

    if location_lat is not None and location_lng is not None:
        doc["_geo"] = {"lat": location_lat, "lng": location_lng}

    if attributes:
        for key, value in attributes.items():
            doc[f"attr_{key}"] = value

    return doc


def sync_resource(
    tenant_id: str,
    resource_type_slug: str,
    document: dict,
) -> None:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)
    try:
        index = client.index(uid)
        index.add_documents([document])
    except meilisearch.errors.MeilisearchApiError:
        pass


def remove_resource(
    tenant_id: str,
    resource_type_slug: str,
    resource_id: str,
) -> None:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)
    try:
        index = client.index(uid)
        index.delete_document(resource_id)
    except meilisearch.errors.MeilisearchApiError:
        pass
