"""
Seed development environment with demo tenant and dummy data.
Creates tenant (localhost), resource types (vehicles/bikes, cooks, apartments),
resources, users, bookings, reviews, and notifications.

Run: docker compose exec backend python -m scripts.seed_demo
"""
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import PlatformUser, Role, User, UserRole
from app.core.notifications.models import Notification
from app.core.tenancy.models import Tenant, TenantDomain
from app.core.tenancy.provisioning import provision_tenant_schema
from app.domains.bookings.models import Booking
from app.domains.resources.models import Resource, ResourceAvailability, ResourceType
from app.domains.resources.templates import RESOURCE_TYPE_TEMPLATES
from app.domains.reviews.models import Review

DB_URL = "postgresql+asyncpg://rentmanager:rentmanager_dev@postgres:5432/rentmanager"


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

TENANT_SLUG = "demo"
TENANT_NAME = "Demo Rentals"
DOMAINS = ["localhost", "demo.localhost", "127.0.0.1"]
PLATFORM_EMAIL = "platform@rentmanager.dev"
PLATFORM_PASSWORD = "platform123"
ADMIN_EMAIL = "admin@rentmanager.dev"
ADMIN_PASSWORD = "admin123"
LISTER_EMAIL = "lister@rentmanager.dev"
LISTER_PASSWORD = "lister123"
CUSTOMERS = [
    ("alice@rentmanager.dev", "alice123", "Alice Johnson"),
    ("bob@rentmanager.dev", "bob123", "Bob Smith"),
]

RESOURCE_TYPE_TEMPLATES_TO_CREATE = ["vehicles", "venues", "cooks"]

VEHICLES = [
    dict(
        name="Royal Enfield Classic 350",
        description="Classic cruiser bike in pristine condition. Perfect for weekend rides.",
        base_price=30.0,
        attributes=dict(
            vehicle_type="bike",
            vehicle_number="HR26 BK 1234",
            engine_number="RE350EN2024001",
            chassis_number="RE350CH2024001",
            year=2024,
            seats=2,
            fuel_type="petrol",
            transmission="manual",
            features=["helmet_included", "phone_mount", "pannier_bags"],
        ),
    ),
    dict(
        name="Honda CBR 650R",
        description="Sport bike with excellent handling. 650cc engine.",
        base_price=45.0,
        attributes=dict(
            vehicle_type="bike",
            vehicle_number="DL8S CBR 5678",
            engine_number="HON650EN2023002",
            chassis_number="HON650CH2023002",
            year=2023,
            seats=2,
            fuel_type="petrol",
            transmission="manual",
            features=["abs", "slipper_clutch", "traction_control"],
        ),
    ),
    dict(
        name="Trek FX 3 Disc",
        description="Electric hybrid bike. Great for city commuting.",
        base_price=15.0,
        attributes=dict(
            vehicle_type="electric_bike",
            vehicle_number="NA",
            engine_number="TREKFXEN2024003",
            chassis_number="TREKFXCH2024003",
            year=2024,
            seats=1,
            fuel_type="none",
            transmission="manual",
            features=["electric_assist", "basket", "lights", "bell"],
        ),
    ),
]

APARTMENTS = [
    dict(
        name="Downtown Studio Apartment",
        description="Modern studio in the heart of the city. Walking distance to metro.",
        base_price=120.0,
        location_address="42 Main Street, Downtown",
        location_lat=40.7128,
        location_lng=-74.0060,
        attributes=dict(
            property_type="apartment",
            bedrooms=0,
            bathrooms=1,
            max_guests=2,
            amenities=["wifi", "ac", "kitchen", "washing_machine", "elevator"],
            pet_friendly=False,
        ),
    ),
    dict(
        name="Luxury 2BR Riverside View",
        description="Premium apartment with stunning river views. Full amenities.",
        base_price=250.0,
        location_address="100 River Road, Riverside",
        location_lat=40.7282,
        location_lng=-73.9942,
        attributes=dict(
            property_type="apartment",
            bedrooms=2,
            bathrooms=2,
            max_guests=6,
            amenities=["wifi", "ac", "kitchen", "parking", "gym", "pool", "doorman"],
            pet_friendly=True,
        ),
    ),
    dict(
        name="Cozy Loft in Arts District",
        description="Converted warehouse loft with high ceilings and natural light.",
        base_price=180.0,
        location_address="25 Gallery Row, Arts District",
        location_lat=40.7209,
        location_lng=-73.9814,
        attributes=dict(
            property_type="apartment",
            bedrooms=1,
            bathrooms=1,
            max_guests=3,
            amenities=["wifi", "ac", "kitchen", "bike_storage", "roof_access"],
            pet_friendly=True,
        ),
    ),
]

COOKS = [
    dict(
        name="Chef Marco Rossi",
        description="Italian chef with 15 years of experience. Specializes in handmade pasta.",
        base_price=80.0,
        attributes=dict(
            cuisine_type=["italian", "mediterranean"],
            experience_years=15,
            specialties=["homemade_pasta", "risotto", "tiramisu", "seafood"],
            max_guests_served=8,
            brings_own_ingredients=True,
        ),
    ),
    dict(
        name="Chef Aisha Kapoor",
        description="North Indian cuisine expert. From street food to royal thalis.",
        base_price=70.0,
        attributes=dict(
            cuisine_type=["indian", "punjabi", "mughlai"],
            experience_years=10,
            specialties=["biryani", "butter_chicken", "naan", "dal_makhani"],
            max_guests_served=12,
            brings_own_ingredients=True,
        ),
    ),
    dict(
        name="Chef Yuki Tanaka",
        description="Japanese chef trained in Tokyo. Sushi, ramen, and kaiseki.",
        base_price=90.0,
        attributes=dict(
            cuisine_type=["japanese", "sushi", "asian"],
            experience_years=12,
            specialties=["sushi", "ramen", "tempura", "miso"],
            max_guests_served=6,
            brings_own_ingredients=True,
        ),
    ),
]

BOOKINGS_DATA = [
    # (resource_name, user_email, status, days_ago, start_hour, duration_hours)
    ("Royal Enfield Classic 350", "alice@rentmanager.dev", "completed", 10, 10, 4),
    ("Downtown Studio Apartment", "bob@rentmanager.dev", "completed", 8, 14, 24),
    ("Chef Marco Rossi", "alice@rentmanager.dev", "completed", 7, 13, 3),
    ("Luxury 2BR Riverside View", "bob@rentmanager.dev", "confirmed", 3, 14, 24),
    ("Honda CBR 650R", "alice@rentmanager.dev", "active", 1, 10, 6),
    ("Chef Aisha Kapoor", "bob@rentmanager.dev", "active", 0, 13, 3),
    ("Cozy Loft in Arts District", "alice@rentmanager.dev", "pending", 0, 14, 24),
    ("Chef Yuki Tanaka", "bob@rentmanager.dev", "confirmed", -5, 19, 2),
    ("Downtown Studio Apartment", "alice@rentmanager.dev", "cancelled", 5, 14, 24),
    ("Trek FX 3 Disc", "bob@rentmanager.dev", "pending", 0, 10, 3),
    ("Royal Enfield Classic 350", "bob@rentmanager.dev", "completed", 12, 8, 5),
    ("Chef Marco Rossi", "alice@rentmanager.dev", "active", 0, 19, 2),
]

REVIEWS_DATA = [
    # (booking_index_in_completed_list, rating, title, body)
    (0, 5, "Amazing bike!", "Smooth ride, excellent condition. Highly recommend!"),
    (1, 4, "Great location", "Clean and well-equipped studio. Would stay again."),
    (2, 5, "Fantastic chef!", "Chef Marco prepared an incredible 3-course Italian meal."),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def today():
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def make_resource(type_id, data, owner_id):
    return Resource(
        id=uuid4(),
        type_id=type_id,
        name=data["name"],
        description=data.get("description"),
        base_price=data["base_price"],
        currency="USD",
        status="active",
        owner_id=owner_id,
        attributes=data.get("attributes"),
        location_address=data.get("location_address"),
        location_lat=data.get("location_lat"),
        location_lng=data.get("location_lng"),
        rating_avg=0.0,
        rating_count=0,
    )


def make_avail(resource_id, start_offset_hours, duration_hours):
    return ResourceAvailability(
        id=uuid4(),
        resource_id=resource_id,
        start_time=today() + timedelta(hours=start_offset_hours),
        end_time=today() + timedelta(hours=start_offset_hours + duration_hours),
        status="available",
    )


# ---------------------------------------------------------------------------
# Seed logic
# ---------------------------------------------------------------------------


async def seed():
    engine = create_async_engine(DB_URL, echo=False)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        # -- 1. Platform user ---------------------------------------------------
        existing = (await session.exec(
            select(PlatformUser).where(PlatformUser.email == PLATFORM_EMAIL)
        )).first()
        if existing:
            print(f"  Platform user exists: {PLATFORM_EMAIL}")
        else:
            pu = PlatformUser(
                id=uuid4(),
                email=PLATFORM_EMAIL,
                password_hash=hash_pw(PLATFORM_PASSWORD),
                full_name="Platform Admin",
            )
            session.add(pu)
            await session.commit()
            print(f"  Created platform user: {PLATFORM_EMAIL}")

        # -- 2. Tenant ---------------------------------------------------------
        existing_tenant = (await session.exec(
            select(Tenant).where(Tenant.slug == TENANT_SLUG)
        )).first()
        if existing_tenant:
            tenant = existing_tenant
            tenant_id_val = tenant.id
            schema_name = str(tenant.schema_name)
            print(f"  Tenant exists: {TENANT_SLUG} (schema: {schema_name})")
        else:
            tenant_id_val = uuid4()
            tenant_id = str(tenant_id_val)
            schema_name = f"tenant_{tenant_id.replace('-', '_')}"
            tenant = Tenant(
                id=tenant_id_val,
                name=TENANT_NAME,
                slug=TENANT_SLUG,
                schema_name=schema_name,
                base_currency="USD",
                timezone="America/New_York",
            )
            session.add(tenant)
            await session.commit()
            await provision_tenant_schema(engine, session, tenant_id)
            print(f"  Created tenant: {TENANT_SLUG} (schema: {schema_name})")

        # -- 3. Tenant domains for localhost ------------------------------------
        await session.execute(text(f"SET search_path TO {schema_name}, public"))
        for domain in DOMAINS:
            existing_domain = (await session.exec(
                select(TenantDomain).where(TenantDomain.domain == domain)
            )).first()
            if not existing_domain:
                td = TenantDomain(
                    id=uuid4(),
                    tenant_id=tenant_id_val,
                    domain=domain,
                    is_primary=(domain == "localhost"),
                    is_verified=True,
                )
                session.add(td)
                print(f"  Created domain: {domain}")
        await session.commit()

        # -- 4. Resource types -------------------------------------------------
        type_map = {}
        for slug in RESOURCE_TYPE_TEMPLATES_TO_CREATE:
            template = RESOURCE_TYPE_TEMPLATES[slug]
            existing_type = (await session.exec(
                select(ResourceType).where(ResourceType.slug == slug)
            )).first()
            if existing_type:
                type_map[slug] = existing_type
                print(f"  Resource type exists: {slug}")
            else:
                rt = ResourceType(
                    id=uuid4(),
                    name=template["name"],
                    slug=template["slug"],
                    icon=template.get("icon"),
                    description=template.get("description"),
                    availability_model=template["availability_model"],
                    pricing_model=template["pricing_model"],
                    attribute_schema=template.get("attribute_schema"),
                    slot_config=template.get("slot_config"),
                    pricing_config=template.get("pricing_config"),
                    cancellation_defaults=template.get("cancellation_defaults"),
                    is_active=True,
                )
                session.add(rt)
                await session.flush()
                type_map[slug] = rt
                print(f"  Created resource type: {slug}")
        await session.commit()

        # -- 5. Users ----------------------------------------------------------
        admin_id = uuid4()
        lister_id = uuid4()
        alice_id = uuid4()
        bob_id = uuid4()

        admin_user = (await session.exec(
            select(User).where(User.email == ADMIN_EMAIL)
        )).first()
        if admin_user:
            admin_id = admin_user.id
            print(f"  Admin exists: {ADMIN_EMAIL}")
        else:
            admin_user = User(
                id=admin_id,
                email=ADMIN_EMAIL,
                password_hash=hash_pw(ADMIN_PASSWORD),
                full_name="Demo Admin",
                is_active=True,
                is_verified=True,
                user_type="admin",
            )
            session.add(admin_user)
            await session.commit()
            admin_role = (await session.exec(
                select(Role).where(Role.slug == "admin")
            )).first()
            if admin_role:
                session.add(UserRole(user_id=admin_id, role_id=admin_role.id))
                await session.commit()
            print(f"  Created admin: {ADMIN_EMAIL}")

        lister_user = (await session.exec(
            select(User).where(User.email == LISTER_EMAIL)
        )).first()
        if lister_user:
            lister_id = lister_user.id
            print(f"  Lister exists: {LISTER_EMAIL}")
        else:
            lister_user = User(
                id=lister_id,
                email=LISTER_EMAIL,
                password_hash=hash_pw(LISTER_PASSWORD),
                full_name="Demo Lister",
                is_active=True,
                is_verified=True,
                user_type="lister",
            )
            session.add(lister_user)
            await session.commit()
            lister_role = (await session.exec(
                select(Role).where(Role.slug == "lister")
            )).first()
            if lister_role:
                session.add(UserRole(user_id=lister_id, role_id=lister_role.id))
                await session.commit()
            print(f"  Created lister: {LISTER_EMAIL}")

        customer_ids = {alice_id: alice_id, bob_id: bob_id}
        for email, pw, name in CUSTOMERS:
            cust = (await session.exec(
                select(User).where(User.email == email)
            )).first()
            if cust:
                customer_ids[email] = cust.id
                print(f"  Customer exists: {email}")
            else:
                cid = customer_ids[email]
                cust = User(
                    id=cid,
                    email=email,
                    password_hash=hash_pw(pw),
                    full_name=name,
                    is_active=True,
                    is_verified=True,
                    user_type="customer",
                )
                session.add(cust)
                await session.commit()
                customer_role = (await session.exec(
                    select(Role).where(Role.slug == "customer")
                )).first()
                if customer_role:
                    session.add(UserRole(user_id=cid, role_id=customer_role.id))
                    await session.commit()
                print(f"  Created customer: {email}")

        alice_id = customer_ids["alice@rentmanager.dev"]
        bob_id = customer_ids["bob@rentmanager.dev"]

        # -- 6. Resources ------------------------------------------------------
        vehicles_type = type_map["vehicles"]
        venues_type = type_map["venues"]
        cooks_type = type_map["cooks"]

        res_by_name = {}

        async def seed_resources(slug, type_id, entries):
            for entry in entries:
                existing = (await session.exec(
                    select(Resource).where(
                        Resource.type_id == type_id,
                        Resource.name == entry["name"],
                    )
                )).first()
                if existing:
                    res_by_name[entry["name"]] = existing
                    print(f"  Resource exists: {entry['name']}")
                else:
                    r = make_resource(type_id, entry, lister_id)
                    session.add(r)
                    await session.flush()
                    res_by_name[entry["name"]] = r
                    print(f"  Created resource: {entry['name']}")

        await seed_resources("vehicles", vehicles_type.id, VEHICLES)
        await seed_resources("venues", venues_type.id, APARTMENTS)
        await seed_resources("cooks", cooks_type.id, COOKS)
        await session.commit()

        # -- 7. Availability slots ---------------------------------------------
        existing_avail = (await session.exec(
            select(ResourceAvailability).limit(1)
        )).first()

        if not existing_avail:
            all_avail = []
            for r in res_by_name.values():
                for day_offset in range(14):
                    if r.type_id == vehicles_type.id:
                        for hour in [8, 10, 12, 14, 16, 18]:
                            all_avail.append(make_avail(r.id, day_offset * 24 + hour, 2))
                    elif r.type_id == venues_type.id:
                        all_avail.append(ResourceAvailability(
                            id=uuid4(),
                            resource_id=r.id,
                            start_time=today() + timedelta(days=day_offset, hours=14),
                            end_time=today() + timedelta(days=day_offset + 1, hours=14),
                            status="available",
                        ))
                    elif r.type_id == cooks_type.id:
                        for hour in [10, 13, 16, 19]:
                            all_avail.append(make_avail(r.id, day_offset * 24 + hour, 2))
            session.add_all(all_avail)
            await session.commit()
            print(f"  Created {len(all_avail)} availability slots")
        else:
            print("  Availability slots already exist")

        # -- 8. Bookings -------------------------------------------------------
        existing_bookings = (await session.exec(select(Booking).limit(1))).first()

        if not existing_bookings:
            resource_by_name = {}
            for name, r in res_by_name.items():
                resource_by_name[name] = r

            created_bookings = []
            for res_name, user_email, status, days_ago, start_hour, duration_hours in BOOKINGS_DATA:
                resource = resource_by_name[res_name]
                uid = alice_id if user_email == "alice@rentmanager.dev" else bob_id
                start = today() - timedelta(days=days_ago) + timedelta(hours=start_hour)
                end = start + timedelta(hours=duration_hours)

                if resource.type_id == vehicles_type.id:
                    total_price = resource.base_price * duration_hours
                elif resource.type_id == venues_type.id:
                    total_price = resource.base_price * max(1, duration_hours // 24)
                else:
                    total_price = resource.base_price

                service_fee = round(total_price * 0.08, 2)
                platform_commission = round(total_price * 0.12, 2)
                owner_payout = total_price - platform_commission
                customer_total = total_price + service_fee

                booking = Booking(
                    id=uuid4(),
                    resource_id=resource.id,
                    user_id=uid,
                    status=status,
                    start_time=start,
                    end_time=end,
                    total_price=total_price,
                    currency="USD",
                    service_fee=service_fee,
                    platform_commission=platform_commission,
                    owner_payout=owner_payout,
                    customer_total=customer_total,
                    auto_confirm=True,
                    confirmed_at=start - timedelta(hours=2) if status in ("confirmed", "active", "completed") else None,
                    cancelled_at=start if status == "cancelled" else None,
                    cancellation_reason="Changed plans" if status == "cancelled" else None,
                    refund_percent=50 if status == "cancelled" else None,
                )
                session.add(booking)
                await session.flush()
                created_bookings.append(booking)

            await session.commit()
            print(f"  Created {len(created_bookings)} bookings")
        else:
            print("  Bookings already exist — skipping")
            result = await session.exec(select(Booking).order_by(Booking.created_at))
            created_bookings = list(result.all())

        # -- 9. Reviews --------------------------------------------------------
        existing_reviews = (await session.exec(select(Review).limit(1))).first()
        completed_bookings = [b for b in created_bookings if b.status == "completed"]

        if not existing_reviews and completed_bookings:
            for idx, rating, title, body in REVIEWS_DATA:
                if idx < len(completed_bookings):
                    b = completed_bookings[idx]
                    existing = (await session.exec(
                        select(Review).where(Review.booking_id == b.id)
                    )).first()
                    if not existing:
                        review = Review(
                            id=uuid4(),
                            booking_id=b.id,
                            resource_id=b.resource_id,
                            reviewer_id=b.user_id,
                            direction="customer_to_lister",
                            rating=rating,
                            title=title,
                            body=body,
                            status="published",
                        )
                        session.add(review)

            await session.commit()
            print(f"  Created {len(REVIEWS_DATA)} reviews")

            # Update resource ratings
            for b in completed_bookings:
                reviews_for = (await session.exec(
                    select(Review).where(
                        Review.resource_id == b.resource_id,
                        Review.status == "published",
                    )
                )).all()
                if reviews_for:
                    rsrc = (await session.exec(
                        select(Resource).where(Resource.id == b.resource_id)
                    )).first()
                    if rsrc:
                        rsrc.rating_avg = round(
                            sum(r.rating for r in reviews_for) / len(reviews_for), 1
                        )
                        rsrc.rating_count = len(reviews_for)
                        session.add(rsrc)
            await session.commit()
            print("  Updated resource ratings")
        else:
            print("  Reviews already exist (or no completed bookings)")

        # -- 10. Notifications -------------------------------------------------
        existing_notifs = (await session.exec(select(Notification).limit(1))).first()

        if not existing_notifs:
            notifications_data = [
                ("booking.new", "New Booking", "Alice booked Royal Enfield Classic 350"),
                ("booking.confirmed", "Booking Confirmed", "Downtown Studio Apartment booking confirmed"),
                ("booking.confirmed", "Booking Confirmed", "Chef Marco Rossi booking for tonight confirmed"),
                ("booking.cancelled", "Booking Cancelled", "Downtown Studio Apartment booking was cancelled"),
                ("booking.new", "New Booking", "Bob booked Luxury 2BR Riverside View"),
                ("booking.confirmed", "Booking Confirmed", "Luxury 2BR Riverside View booking confirmed"),
                ("booking.completed", "Booking Completed", "Royal Enfield Classic 350 rental completed"),
                ("booking.completed", "Booking Completed", "Downtown Studio Apartment stay completed"),
                ("review.received", "New Review", "Alice left a 5-star review for Royal Enfield Classic 350"),
                ("review.received", "New Review", "Bob left a 4-star review for Downtown Studio Apartment"),
            ]

            for event_type, title, body in notifications_data:
                n = Notification(
                    id=uuid4(),
                    user_id=admin_id,
                    event_type=event_type,
                    title=title,
                    body=body,
                    is_read=False,
                    created_at=today() - timedelta(hours=len(notifications_data) - notifications_data.index((event_type, title, body))),
                )
                session.add(n)

            await session.commit()
            print(f"  Created {len(notifications_data)} notifications")
        else:
            print("  Notifications already exist")

        # -- 11. Sync resources to Meilisearch ---------------------------------
        try:
            from app.core.search.tasks import full_reindex
            count = await full_reindex(session, str(tenant_id_val))
            if count:
                print(f"  Synced {count} resources to Meilisearch")
        except Exception as e:
            print(f"  Meilisearch sync skipped ({e})")

        await session.execute(text("SET search_path TO public"))

    await engine.dispose()

    # -----------------------------------------------------------------------
    # Print summary
    # -----------------------------------------------------------------------
    print()
    print("=" * 55)
    print("  DEMO SEED COMPLETE")
    print("=" * 55)
    print(f"  Tenant slug:  {TENANT_SLUG}")
    print(f"  Domains:       {', '.join(DOMAINS)}")
    print()
    print("  USERS")
    print(f"    Admin:      {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"    Lister:     {LISTER_EMAIL} / {LISTER_PASSWORD}")
    for email, pw, _ in CUSTOMERS:
        print(f"    Customer:   {email} / {pw}")
    print()
    print("  RESOURCE TYPES: vehicles, venues, cooks")
    print("  RESOURCES:")
    for v in VEHICLES:
        print(f"    - {v['name']} (${v['base_price']}/hr)")
    for a in APARTMENTS:
        print(f"    - {a['name']} (${a['base_price']}/night)")
    for c in COOKS:
        print(f"    - {c['name']} (${c['base_price']}/slot)")
    print()
    print("  Login at http://localhost:3000")
    print("  (frontend auto-resolves tenant via localhost domain)")
    print("=" * 55)
    print()


if __name__ == "__main__":
    asyncio.run(seed())
