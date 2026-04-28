import meilisearch

from app.config import get_settings


def get_meili_client() -> meilisearch.Client:
    settings = get_settings()
    return meilisearch.Client(settings.meili_url, settings.meili_master_key)


def get_index_uid(tenant_id: str, resource_type_slug: str) -> str:
    safe_tenant = tenant_id.replace("-", "_")
    safe_slug = resource_type_slug.replace("-", "_")
    return f"t_{safe_tenant}_{safe_slug}"
