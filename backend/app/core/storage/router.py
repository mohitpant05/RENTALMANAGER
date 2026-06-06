import logging
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.auth.models import User
from app.core.storage.schemas import AttachmentResponse
from app.core.storage.service import (
    create_attachment,
    delete_attachment,
    generate_download_url,
    get_attachment,
    list_attachments,
    proxy_file,
    upload_file,
)
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

logger = logging.getLogger("app.storage.router")

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/proxy/{bucket}/{file_path:path}")
def serve_proxied_file(bucket: str, file_path: str):
    """Serve a file from MinIO through the backend — no direct browser-to-MinIO."""
    slug = bucket.replace("tenant-", "", 1) if bucket.startswith("tenant-") else bucket
    data, content_type, content_length = proxy_file(slug, file_path)
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Length": str(content_length),
            "Cache-Control": "public, max-age=86400",
        },
    )


@router.post("/upload", response_model=AttachmentResponse, status_code=201)
async def direct_upload(
    file: UploadFile,
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    purpose: str = Form("image"),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    print(f"=== UPLOAD DEBUG: file={file.filename} content_type={file.content_type} "
          f"entity_type={entity_type} entity_id={entity_id} purpose={purpose} "
          f"user={user.id}", flush=True)

    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_MIME_TYPES)}",
        )

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10 MB.")

    file_path = upload_file(
        tenant_ctx.tenant.slug,
        entity_type,
        entity_id,
        file.filename or "unnamed",
        data,
        file.content_type or "application/octet-stream",
    )

    attachment = await create_attachment(
        session,
        entity_type=entity_type,
        entity_id=uuid.UUID(entity_id),
        file_path=file_path,
        file_name=file.filename or "unnamed",
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(data),
        purpose=purpose,
        uploaded_by=user.id,
    )

    url = generate_download_url(tenant_ctx.tenant.slug, attachment.file_path)
    resp = AttachmentResponse.model_validate(attachment)
    resp.download_url = url
    return resp


@router.get("/attachments", response_model=list[AttachmentResponse])
async def list_entity_attachments(
    entity_type: str = Query(...),
    entity_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    attachments = await list_attachments(session, entity_type, entity_id)
    results = []
    for a in attachments:
        resp = AttachmentResponse.model_validate(a)
        resp.download_url = generate_download_url(
            tenant_ctx.tenant.slug, a.file_path
        )
        results.append(resp)
    return results


@router.get("/attachments/{attachment_id}", response_model=AttachmentResponse)
async def get_one_attachment(
    attachment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    attachment = await get_attachment(session, attachment_id)
    resp = AttachmentResponse.model_validate(attachment)
    resp.download_url = generate_download_url(
        tenant_ctx.tenant.slug, attachment.file_path
    )
    return resp


@router.delete("/attachments/{attachment_id}", status_code=204)
async def delete_one_attachment(
    attachment_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    is_admin = user.user_type == "admin"
    await delete_attachment(
        session, attachment_id, user.id, tenant_ctx.tenant.slug, is_admin=is_admin
    )
