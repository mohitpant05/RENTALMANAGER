"""
Seed addon assignments for demo tenant.

Run after seed_demo.py to link cooks & vehicles to venues so they appear
as available addons on the public resource detail page.

Usage:
    docker compose exec backend python -m scripts.seed_addons
"""
import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import User
from app.core.tenancy.models import Tenant
from app.domains.resources.models import Resource, ResourceAssignment, ResourceAvailability, ResourceType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_addons")

DB_URL = "postgresql+asyncpg://rentmanager:rentmanager_dev@postgres:5432/rentmanager"


async def seed():
    engine = create_async_engine(DB_URL, echo=False)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        await session.execute(text("SET search_path TO public"))

        tenant = (await session.exec(
            select(Tenant).where(Tenant.slug == "demo")
        )).first()
        if not tenant:
            logger.error("Demo tenant not found — run seed_demo.py first")
            return
        await session.execute(text(f"SET search_path TO {tenant.schema_name}, public"))

        # Get resource types
        venues_type = (await session.exec(
            select(ResourceType).where(ResourceType.slug == "venues")
        )).first()
        cooks_type = (await session.exec(
            select(ResourceType).where(ResourceType.slug == "cooks")
        )).first()
        vehicles_type = (await session.exec(
            select(ResourceType).where(ResourceType.slug == "vehicles")
        )).first()

        if not all([venues_type, cooks_type, vehicles_type]):
            logger.error("Run seed_demo.py first — resource types not found")
            return

        # Update roles
        changed = False
        if venues_type.role != "primary":
            venues_type.role = "primary"
            session.add(venues_type)
            changed = True
            logger.info("Updated venues type role → primary")

        if cooks_type.role != "addon":
            cooks_type.role = "addon"
            cooks_type.discovery_radius_km = 5.0
            session.add(cooks_type)
            changed = True
            logger.info("Updated cooks type role → addon (radius 5km)")

        if vehicles_type.role != "addon":
            vehicles_type.role = "addon"
            vehicles_type.discovery_radius_km = 10.0
            session.add(vehicles_type)
            changed = True
            logger.info("Updated vehicles type role → addon (radius 10km)")

        if changed:
            await session.commit()
            await session.refresh(venues_type)
            await session.refresh(cooks_type)
            await session.refresh(vehicles_type)

        # Get all resources
        venues = (await session.exec(
            select(Resource).where(Resource.type_id == venues_type.id)
        )).all()
        cooks = (await session.exec(
            select(Resource).where(Resource.type_id == cooks_type.id)
        )).all()
        vehicles = (await session.exec(
            select(Resource).where(Resource.type_id == vehicles_type.id)
        )).all()

        if not venues or not (cooks or vehicles):
            logger.warning("No venues or addon resources found — nothing to assign")
            return

        admin_user = (await session.exec(
            select(User).where(User.email == "admin@rentmanager.dev")
        )).first()
        if not admin_user:
            logger.warning("Admin user not found — skipping assignments")
            return
        admin_id = admin_user.id

        assignment_count = 0
        for venue in venues:
            for addon in list(cooks) + list(vehicles):
                existing = (await session.exec(
                    select(ResourceAssignment).where(
                        ResourceAssignment.primary_resource_id == venue.id,
                        ResourceAssignment.addon_resource_id == addon.id,
                    )
                )).first()
                if existing:
                    continue
                session.add(ResourceAssignment(
                    id=uuid4(),
                    primary_resource_id=venue.id,
                    addon_resource_id=addon.id,
                    priority=0,
                    assigned_by=admin_id,
                ))
                assignment_count += 1

        if assignment_count > 0:
            await session.commit()
            logger.info("Created %d ResourceAssignment records", assignment_count)
        else:
            logger.info("No new assignments needed")

        # Create availability for addons if none exists
        for addon_list, label in [(cooks, "cooks"), (vehicles, "vehicles")]:
            for r in addon_list:
                existing = (await session.exec(
                    select(ResourceAvailability).where(
                        ResourceAvailability.resource_id == r.id,
                        ResourceAvailability.status == "available",
                    ).limit(1)
                )).first()
                if existing:
                    continue

                today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                avail_records = []
                for day_offset in range(30):
                    if label == "cooks":
                        for hour in [9, 12, 15, 18]:
                            avail_records.append(
                                ResourceAvailability(
                                    id=uuid4(),
                                    resource_id=r.id,
                                    start_time=today + timedelta(days=day_offset, hours=hour),
                                    end_time=today + timedelta(days=day_offset, hours=hour + 3),
                                    status="available",
                                )
                            )
                    elif label == "vehicles":
                        avail_records.append(
                            ResourceAvailability(
                                id=uuid4(),
                                resource_id=r.id,
                                start_time=today + timedelta(days=day_offset, hours=8),
                                end_time=today + timedelta(days=day_offset, hours=20),
                                status="available",
                            )
                        )
                session.add_all(avail_records)
                await session.flush()
                logger.info("Created availability for %s (%s)", r.name, label)

        await session.commit()
        logger.info("Addon seed complete")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
