import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.admin.schemas import ListerInvite
from app.core.auth.models import Role, User, UserRole


async def list_listers(
    session: AsyncSession,
    manager_id: uuid.UUID | None = None,
) -> list[dict]:
    stmt = select(User).where(User.user_type == "lister")
    if manager_id is not None:
        stmt = stmt.where(User.manager_id == manager_id)
    stmt = stmt.order_by(User.created_at.desc())
    result = await session.exec(stmt)
    users = list(result.all())

    lister_list = []
    for u in users:
        roles_result = await session.exec(
            select(Role.slug)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == u.id)
        )
        roles = list(roles_result.all())
        lister_list.append({**u.model_dump(), "roles": roles})
    return lister_list


async def invite_lister(
    session: AsyncSession,
    data: ListerInvite,
    manager_id: uuid.UUID,
    tenant_id: str,
    tenant_slug: str,
) -> tuple[User, str, str | None]:
    from app.core.admin.schemas import StaffInvite
    from app.core.admin.service import invite_staff

    staff_data = StaffInvite(
        email=data.email,
        full_name=data.full_name,
        user_type="lister",
        role_slugs=data.role_slugs,
    )
    user, email_status, email_warning = await invite_staff(
        session, staff_data, tenant_id, tenant_slug,
    )
    user.manager_id = manager_id
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, email_status, email_warning
