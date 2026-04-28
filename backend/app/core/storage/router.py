import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.dependencies import get_current_user
from app.core.auth.models import User
from app.core.storage.schemas import (
    AttachmentResponse,
    ConfirmUploadRequest,
    UploadRequest,
    UploadResponse,
)
from app.core.storage.service import (
    create_attachment,
    delete_attachment,
    generate_download_url,
    generate_upload_url,
    get_attachment,
    list_attachments,
)
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.post("/upload-url", response_model=UploadResponse)
async def request_upload_url(
    data: UploadRequest,
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    result = generate_upload_url(
        tenant_ctx.tenant.slug,
        data.entity_type,
        str(data.entity_id),
        data.file_name,
        data.mime_type,
    )
    return UploadResponse(**result)


@router.post("/confirm", response_model=AttachmentResponse, status_code=201)
async def confirm_upload(
    data: ConfirmUploadRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tenant_ctx = get_current_tenant()
    if tenant_ctx is None:
        raise HTTPException(status_code=400, detail="Tenant context required")
    attachment = await create_attachment(
        session,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        file_path=data.file_path,
        file_name=data.file_name,
        mime_type=data.mime_type,
        file_size=data.file_size,
        purpose=data.purpose,
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
