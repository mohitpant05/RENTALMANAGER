import uuid
from datetime import timedelta

from fastapi import HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.storage.client import ensure_bucket, get_minio_client, get_tenant_bucket
from app.core.storage.models import Attachment


def generate_upload_url(
    tenant_slug: str,
    entity_type: str,
    entity_id: str,
    file_name: str,
    mime_type: str = "application/octet-stream",
    expires_minutes: int = 15,
) -> dict:
    client = get_minio_client()
    bucket = get_tenant_bucket(tenant_slug)
    ensure_bucket(client, bucket)

    file_path = f"{entity_type}/{entity_id}/{uuid.uuid4().hex}_{file_name}"
    url = client.presigned_put_object(
        bucket, file_path, expires=timedelta(minutes=expires_minutes)
    )
    return {
        "upload_url": url,
        "file_path": file_path,
        "bucket": bucket,
    }


def generate_download_url(
    tenant_slug: str,
    file_path: str,
    expires_minutes: int = 60,
) -> str:
    client = get_minio_client()
    bucket = get_tenant_bucket(tenant_slug)
    return client.presigned_get_object(
        bucket, file_path, expires=timedelta(minutes=expires_minutes)
    )


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
