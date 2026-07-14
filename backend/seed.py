import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlmodel import select

from app.core.auth.models import Role, User, UserRole
from app.core.auth.password import hash_password
from app.database import async_session_factory
from app.domains.bookings.models import Booking
from app.domains.resources.models import Resource, ResourceType

SCHEMA = "tenant_test_f9bb0dd4"
ADMIN_ID = "c859c1f6-81ad-46c9-b2f1-21d4c3a6baae"


async def seed():
    async with async_session_factory() as session:
        await session.execute(text(f"SET search_path TO {SCHEMA}, public"))

        roles = {}
        for slug in ["admin", "staff", "lister", "customer"]:
            r = await session.exec(select(Role).where(Role.slug == slug))
            roles[slug] = r.first()

        # --- Customers ---
        customers = []
        customer_data = [
            ("john@example.com", "John Smith", "+1234567890"),
            ("jane@example.com", "Jane Doe", "+1234567891"),
            ("alex@example.com", "Alex Johnson", "+1234567892"),
            ("sarah@example.com", "Sarah Wilson", "+1234567893"),
            ("mike@example.com", "Mike Brown", "+1234567894"),
        ]
        for email, name, phone in customer_data:
            u = User(
                email=email,
                password_hash=hash_password("password123"),
                full_name=name,
                phone=phone,
                user_type="customer",
                is_active=True,
                is_verified=True,
            )
            session.add(u)
            customers.append(u)
        await session.flush()
        for c in customers:
            session.add(UserRole(user_id=c.id, role_id=roles["customer"].id))

        # --- Lister ---
        lister = User(
            email="lister@example.com",
            password_hash=hash_password("password123"),
            full_name="Demo Lister",
            phone="+1234567800",
            user_type="lister",
            is_active=True,
            is_verified=True,
        )
        session.add(lister)
        await session.flush()
        session.add(UserRole(user_id=lister.id, role_id=roles["lister"].id))

        # --- Staff ---
        staff = User(
            email="staff@example.com",
            password_hash=hash_password("password123"),
            full_name="Demo Staff",
            phone="+1234567801",
            user_type="staff",
            is_active=True,
            is_verified=True,
        )
        session.add(staff)
        await session.flush()
        session.add(UserRole(user_id=staff.id, role_id=roles["staff"].id))

        # --- Resource Types ---
        rt_meeting = ResourceType(
            name="Meeting Room",
            slug="meeting-room",
            icon="door-open",
            description="Conference and meeting rooms",
            availability_model="time_slot",
            pricing_model="fixed_per_slot",
            booking_mode="individual",
            role="primary",
            buffer_minutes=15,
            staff_booking_auto_confirm=True,
            requires_verification=False,
            display_order=1,
            is_active=True,
            slot_config={"duration_minutes": 60, "start_hour": 8, "end_hour": 20},
            operating_hours={
                "mon": {"open": "08:00", "close": "20:00"},
                "tue": {"open": "08:00", "close": "20:00"},
                "wed": {"open": "08:00", "close": "20:00"},
                "thu": {"open": "08:00", "close": "20:00"},
                "fri": {"open": "08:00", "close": "18:00"},
            },
        )
        rt_desk = ResourceType(
            name="Hot Desk",
            slug="hot-desk",
            icon="monitor",
            description="Shared workspace desks",
            availability_model="date_range",
            pricing_model="fixed_per_day",
            booking_mode="individual",
            role="primary",
            buffer_minutes=0,
            staff_booking_auto_confirm=True,
            requires_verification=False,
            display_order=2,
            is_active=True,
        )
        rt_parking = ResourceType(
            name="Parking Spot",
            slug="parking-spot",
            icon="car",
            description="Reserved parking spaces",
            availability_model="date_range",
            pricing_model="fixed_per_day",
            booking_mode="individual",
            role="primary",
            buffer_minutes=0,
            staff_booking_auto_confirm=True,
            requires_verification=False,
            display_order=3,
            is_active=True,
        )
        rt_projector = ResourceType(
            name="Projector",
            slug="projector",
            icon="presentation",
            description="Add-on projector for meeting rooms",
            availability_model="time_slot",
            pricing_model="fixed_per_slot",
            booking_mode="bundled",
            role="addon",
            buffer_minutes=0,
            staff_booking_auto_confirm=True,
            requires_verification=False,
            display_order=4,
            is_active=True,
            slot_config={"duration_minutes": 60, "start_hour": 8, "end_hour": 20},
        )
        for rt in [rt_meeting, rt_desk, rt_parking, rt_projector]:
            session.add(rt)
        await session.flush()

        # --- Resources ---
        now = datetime.now(UTC)
        resources = []
        resource_data = [
            (rt_meeting.id, "Boardroom A", "Executive boardroom with 12 seats", 150.0, lister.id),
            (rt_meeting.id, "Meeting Room B", "Small meeting room, 6 seats", 75.0, lister.id),
            (rt_meeting.id, "Conference Hall", "Large hall, 50 seats, stage area", 500.0, lister.id),
            (rt_desk.id, "Desk Zone Alpha", "Open plan area, near window", 25.0, lister.id),
            (rt_desk.id, "Desk Zone Beta", "Quiet zone, sound-proofed", 30.0, lister.id),
            (rt_desk.id, "Standing Desk 1", "Adjustable standing desk", 35.0, lister.id),
            (rt_parking.id, "P1 - Ground Level", "Covered parking, ground floor", 15.0, uuid.UUID(ADMIN_ID)),
            (rt_parking.id, "P2 - Basement", "Basement level, shaded", 10.0, uuid.UUID(ADMIN_ID)),
            (rt_projector.id, "Epson Pro 4K", "4K projector with HDMI", 50.0, lister.id),
            (rt_projector.id, "Portable Projector", "Compact, wireless capable", 30.0, lister.id),
        ]
        for type_id, name, desc, price, owner_id in resource_data:
            r = Resource(
                type_id=type_id,
                name=name,
                description=desc,
                base_price=price,
                currency="USD",
                status="active",
                rating_avg=0.0,
                rating_count=0,
                owner_id=owner_id,
                version=1,
                location_lat=28.6139,
                location_lng=77.2090,
                location_address="New Delhi, India",
            )
            session.add(r)
            resources.append(r)
        await session.flush()

        # --- Bookings ---
        booking_data = [
            (0, 0, 1, 2, "confirmed"),
            (0, 1, 2, 1, "pending"),
            (1, 2, 1, 1, "confirmed"),
            (1, 3, 3, 2, "confirmed"),
            (2, 0, 5, 3, "pending"),
            (3, 1, 1, 0, "confirmed"),
            (3, 4, 2, 0, "confirmed"),
            (4, 2, 1, 0, "pending"),
            (5, 3, 3, 0, "confirmed"),
            (6, 0, 1, 0, "confirmed"),
            (6, 4, 2, 0, "confirmed"),
            (7, 1, 4, 0, "pending"),
            (0, 2, -2, 2, "completed"),
            (1, 0, -5, 1, "completed"),
            (3, 4, -3, 0, "completed"),
            (0, 3, -1, 1, "cancelled"),
        ]
        for res_idx, cust_idx, days, hours, bk_status in booking_data:
            resource = resources[res_idx]
            customer = customers[cust_idx]
            start = now + timedelta(days=days, hours=9)
            end = start + timedelta(hours=max(hours, 8))
            b = Booking(
                resource_id=resource.id,
                user_id=customer.id,
                status=bk_status,
                start_time=start,
                end_time=end,
                total_price=resource.base_price * max(hours, 1),
                currency="USD",
                service_fee=resource.base_price * 0.1,
                platform_commission=resource.base_price * 0.15,
                owner_payout=resource.base_price * 0.85,
                customer_total=resource.base_price * max(hours, 1) + resource.base_price * 0.1,
                auto_confirm=True,
                timezone="Asia/Kolkata",
                version=1,
                confirmed_at=now if bk_status in ("confirmed", "completed") else None,
                cancelled_at=now - timedelta(hours=2) if bk_status == "cancelled" else None,
                cancellation_reason="Schedule changed" if bk_status == "cancelled" else None,
            )
            session.add(b)

        await session.commit()
        await session.execute(text("SET search_path TO public"))

        print("=== SEED COMPLETE ===")
        print(f"Customers: {len(customers)}")
        print("Lister: 1 (lister@example.com)")
        print("Staff: 1 (staff@example.com)")
        print("Resource Types: 4")
        print(f"Resources: {len(resources)}")
        print(f"Bookings: {len(booking_data)}")
        print()
        print("All passwords: password123")


asyncio.run(seed())
