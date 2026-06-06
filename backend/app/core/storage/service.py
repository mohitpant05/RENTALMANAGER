import io
import uuid

from fastapi import HTTPException
from minio.error import S3Error
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.storage.client import ensure_bucket, get_minio_client, get_tenant_bucket
from app.core.storage.models import Attachment


def proxy_url(tenant_slug: str, file_path: str) -> str:
    """Return a backend-proxied URL for the file — no direct MinIO access."""
    bucket = get_tenant_bucket(tenant_slug)
    return f"/api/storage/proxy/{bucket}/{file_path}"


def proxy_file(tenant_slug: str, file_path: str) -> tuple[bytes, str, int]:
    """Fetch file bytes + content-type from MinIO (used by the proxy endpoint)."""
    client = get_minio_client()
    bucket = get_tenant_bucket(tenant_slug)
    try:
        response = client.get_object(bucket, file_path)
        data = response.read()
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        content_length = response.headers.get("Content-Length", "0")
        response.close()
        response.release_conn()
        return data, content_type, int(content_length)
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=500, detail="Storage error")


def upload_file(
    tenant_slug: str,
    entity_type: str,
    entity_id: str,
    file_name: str,
    file_data: bytes,
    mime_type: str,
) -> str:
    client = get_minio_client()
    bucket = get_tenant_bucket(tenant_slug)
    ensure_bucket(client, bucket)

    file_path = f"{entity_type}/{entity_id}/{uuid.uuid4().hex}_{file_name}"
    client.put_object(
        bucket,
        file_path,
        io.BytesIO(file_data),
        length=len(file_data),
        content_type=mime_type,
    )
    return file_path


def generate_download_url(
    tenant_slug: str,
    file_path: str,
    expires_minutes: int = 60,
) -> str:
    # Return a backend-proxied URL instead of a presigned MinIO URL.
    # The proxy endpoint streams the file through the backend,
    # so the browser never connects to MinIO directly.
    return proxy_url(tenant_slug, file_path)


def delete_file(tenant_slug: str, file_path: str) -> None:
    client = get_minio_client()
    bucket = get_tenant_bucket(tenant_slug)
    client.remove_object(bucket, file_path)


async def create_attachment(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    file_path: str,
    file_name: str,
    mime_type: str,
    file_size: int,
    purpose: str,
    uploaded_by: uuid.UUID,
) -> Attachment:
    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        file_path=file_path,
        file_name=file_name,
        mime_type=mime_type,
        file_size=file_size,
        purpose=purpose,
        uploaded_by=uploaded_by,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    return attachment


async def list_attachments(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
) -> list[Attachment]:
    result = await session.exec(
        select(Attachment)
        .where(
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        )
        .order_by(Attachment.created_at.desc())
    )
    return list(result.all())


async def get_attachment(
    session: AsyncSession, attachment_id: uuid.UUID
) -> Attachment:
    result = await session.exec(
        select(Attachment).where(Attachment.id == attachment_id)
    )
    attachment = result.first()
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return attachment


async def delete_attachment(
    session: AsyncSession,
    attachment_id: uuid.UUID,
    user_id: uuid.UUID,
    tenant_slug: str,
    is_admin: bool = False,
) -> None:
    attachment = await get_attachment(session, attachment_id)
    if not is_admin and attachment.uploaded_by != user_id:
        raise HTTPException(status_code=403, detail="Not the file owner")

    delete_file(tenant_slug, attachment.file_path)
    await session.delete(attachment)
    await session.commit()
