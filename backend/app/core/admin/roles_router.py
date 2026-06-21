import uuid

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.roles_schemas import (
    PermissionGroup,
    RoleCreate,
    RolePermissionsUpdate,
    RoleResponse,
    RoleUpdate,
    StaffRolesUpdate,
)
from app.core.admin.roles_service import (
    create_role,
    delete_role,
    get_role,
    list_permissions_grouped,
    list_roles,
    set_role_permissions,
    update_role,
    update_staff_roles,
)
from app.core.admin.schemas import StaffUserResponse
from app.core.admin.service import list_staff
from app.core.auth.dependencies import require_permission
from app.core.auth.models import User
from app.database import get_db

router = APIRouter(prefix="/api/admin", tags=["admin-roles"])


def _require_staff_manage():
    return require_permission("staff:*:manage")


@router.get("/roles", response_model=list[RoleResponse])
async def list_all_roles(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_staff_manage()),
):
    return await list_roles(session)


@router.post("/roles", response_model=RoleResponse, status_code=201)
async def create_new_role(
    data: RoleCreate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_staff_manage()),
):
    return await create_role(session, data)


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_single_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_staff_manage()),
):
    return await get_role(session, role_id)


@router.patch("/roles/{role_id}", response_model=RoleResponse)
async def update_existing_role(
    role_id: uuid.UUID,
    data: RoleUpdate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_staff_manage()),
):
    return await update_role(session, role_id, data)


@router.delete("/roles/{role_id}", status_code=204)
async def delete_existing_role(
    role_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_staff_manage()),
):
    await delete_role(session, role_id)


@router.put("/roles/{role_id}/permissions", response_model=RoleResponse)
async def replace_role_permissions(
    role_id: uuid.UUID,
    data: RolePermissionsUpdate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_staff_manage()),
):
    return await set_role_permissions(session, role_id, data.permission_ids)


@router.get("/permissions", response_model=list[PermissionGroup])
async def list_all_permissions(
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_staff_manage()),
):
    return await list_permissions_grouped(session)


@router.patch("/staff/{user_id}/roles", response_model=StaffUserResponse)
async def update_staff_user_roles(
    user_id: uuid.UUID,
    data: StaffRolesUpdate,
    session: AsyncSession = Depends(get_db),
    _user: User = Depends(_require_staff_manage()),
):
    await update_staff_roles(session, user_id, data.role_ids)
    staff_list = await list_staff(session)
    for s in staff_list:
        if str(s["id"]) == str(user_id):
            return StaffUserResponse(**s)
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="User not found")
