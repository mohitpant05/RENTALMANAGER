from minio import Minio

from app.config import get_settings


def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,
    )


def get_tenant_bucket(tenant_slug: str) -> str:
    safe = tenant_slug.replace("_", "-").lower()
    return f"tenant-{safe}"


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
