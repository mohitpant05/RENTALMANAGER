import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.listers_service import invite_lister, list_listers
from app.core.admin.schemas import ListerInvite, ListerResponse
from app.core.admin.service import activate_user, deactivate_user
from app.core.auth.dependencies import require_permission
from app.core.auth.models import User
from app.core.auth.scoping import resolve_data_scope
from app.core.tenancy.context import get_current_tenant
from app.database import get_db

router = APIRouter(prefix="/api/admin/listers", tags=["admin-listers"])


@router.get("", response_model=list[ListerResponse])
async def list_tenant_listers(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("listers:*:read")),
):
    scope = await resolve_data_scope(session, user)
    if scope.scope_type == "staff":
        manager_filter = user.id
    elif scope.scope_type == "lister":
        raise HTTPException(status_code=403, detail="Listers cannot list other listers")
    else:
        manager_filter = None  # admin sees all
    listers = await list_listers(session, manager_id=manager_filter)
    return [ListerResponse(**l) for l in listers]


@router.post("", response_model=ListerResponse, status_code=201)
async def invite_tenant_lister(
    data: ListerInvite,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("listers:*:invite")),
):
    if user.user_type not in ("admin", "staff"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Only staff or admin can invite listers")

    tenant_ctx = get_current_tenant()
    new_user, email_status, email_warning = await invite_lister(
        session, data,
        manager_id=user.id,
        tenant_id=str(tenant_ctx.tenant.id),
        tenant_slug=tenant_ctx.tenant.slug,
    )
    resp = ListerResponse.model_validate(new_user)
    resp.email_status = email_status
    resp.email_warning = email_warning
    return resp


@router.post("/{user_id}/deactivate", response_model=ListerResponse)
async def deactivate_lister(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("listers:*:manage")),
):
    target = (await session.exec(select(User).where(User.id == user_id))).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.user_type != "lister":
        raise HTTPException(status_code=400, detail="User is not a lister")
    deactivated = await deactivate_user(session, user_id)
    return ListerResponse.model_validate(deactivated)


@router.post("/{user_id}/activate", response_model=ListerResponse)
async def activate_lister(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("listers:*:manage")),
):
    target = (await session.exec(select(User).where(User.id == user_id))).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.user_type != "lister":
        raise HTTPException(status_code=400, detail="User is not a lister")
    activated = await activate_user(session, user_id)
    return ListerResponse.model_validate(activated)
