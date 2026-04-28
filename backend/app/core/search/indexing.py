import meilisearch

from app.core.search.client import get_index_uid, get_meili_client


def create_resource_type_index(
    tenant_id: str,
    resource_type_slug: str,
    attribute_schema: list[dict] | None = None,
) -> str:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)

    client.create_index(uid, {"primaryKey": "id"})

    filterable = ["status", "base_price", "rating_avg", "type_slug", "_geo"]
    sortable = ["base_price", "rating_avg", "created_at", "_geo"]
    searchable = ["name", "description", "location_address"]

    if attribute_schema:
        for attr in attribute_schema:
            attr_name = f"attr_{attr['name']}"
            if attr.get("filterable"):
                filterable.append(attr_name)
            searchable.append(attr_name)

    index = client.index(uid)
    index.update_filterable_attributes(filterable)
    index.update_sortable_attributes(sortable)
    index.update_searchable_attributes(searchable)
    index.update_settings({"displayedAttributes": ["*"]})

    return uid


def delete_resource_type_index(tenant_id: str, resource_type_slug: str) -> None:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)
    try:
        client.delete_index(uid)
    except meilisearch.errors.MeilisearchApiError:
        pass


def configure_geo(tenant_id: str, resource_type_slug: str) -> None:
    client = get_meili_client()
    uid = get_index_uid(tenant_id, resource_type_slug)
    index = client.index(uid)
    current_sortable = index.get_sortable_attributes()
    if "_geo" not in current_sortable:
        index.update_sortable_attributes(current_sortable + ["_geo"])
    current_filterable = index.get_filterable_attributes()
    if "_geo" not in current_filterable:
        index.update_filterable_attributes(current_filterable + ["_geo"])
