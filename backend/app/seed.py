"""
Seed script — creates a demo tenant with ~200 resources across 3 types.

Usage:
    cd backend
    python -m app.seed              # seed with defaults
    python -m app.seed --reset      # drop existing demo data and re-seed
"""
import asyncio
import random
import sys
import uuid

from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.auth.models import Role, User, UserRole
from app.core.auth.password import hash_password
from app.core.search.indexing import create_resource_type_index
from app.core.search.sync import build_document, sync_resource
from app.core.tenancy.models import Tenant
from app.core.tenancy.provisioning import provision_tenant_schema
from app.database import async_session_factory, engine
from app.domains.resources.models import Resource, ResourceType
from app.domains.resources.templates import RESOURCE_TYPE_TEMPLATES

DEMO_TENANT_SLUG = "demo"
DEMO_TENANT_NAME = "Demo Corp"
ADMIN_EMAIL = "admin@demo.com"
ADMIN_PASSWORD = "admin123"
CUSTOMER_EMAIL = "customer@demo.com"
CUSTOMER_PASSWORD = "customer123"
LISTER_EMAIL = "lister@demo.com"
LISTER_PASSWORD = "lister123"

INDIAN_LOCATIONS = [
    ("Mumbai", 19.0760, 72.8777),
    ("Delhi", 28.7041, 77.1025),
    ("Bangalore", 12.9716, 77.5946),
    ("Chennai", 13.0827, 80.2707),
    ("Kolkata", 22.5726, 88.3639),
    ("Hyderabad", 17.3850, 78.4867),
    ("Pune", 18.5204, 73.8567),
    ("Ahmedabad", 23.0225, 72.5714),
    ("Jaipur", 26.9124, 75.7873),
    ("Goa", 15.2993, 74.1240),
    ("Shimla", 31.1048, 77.1734),
    ("Manali", 32.2396, 77.1887),
    ("Udaipur", 24.5854, 73.7125),
    ("Kochi", 9.9312, 76.2673),
    ("Mysore", 12.2958, 76.6394),
    ("Rishikesh", 30.0869, 78.2676),
    ("Varanasi", 25.3176, 83.0064),
    ("Amritsar", 31.6340, 74.8723),
    ("Darjeeling", 27.0410, 88.2663),
    ("Ooty", 11.4102, 76.6950),
    ("Lonavala", 18.7546, 73.4062),
    ("Coorg", 12.3375, 75.8069),
    ("Pondicherry", 11.9416, 79.8083),
    ("Leh", 34.1526, 77.5771),
    ("Chandigarh", 30.7333, 76.7794),
    ("Indore", 22.7196, 75.8577),
    ("Lucknow", 26.8467, 80.9462),
    ("Bhopal", 23.2599, 77.4126),
    ("Nagpur", 21.1458, 79.0882),
    ("Surat", 21.1702, 72.8311),
]

VENUE_NAMES = [
    "Sunrise Villa", "Lake View Apartment", "Mountain Retreat", "Heritage Haveli",
    "Garden Studio", "Penthouse Suite", "Beach House", "River Cottage",
    "Forest Lodge", "Royal Palace Stay", "Hilltop Bungalow", "City Center Flat",
    "Cozy Nest Studio", "Panorama Heights", "Zen Garden Home", "Rustic Farmhouse",
    "Blue Lagoon Villa", "Terrace Garden Flat", "Art Deco Loft", "Colonial Mansion",
    "Palm Grove Cottage", "Sky Lounge Suite", "Bamboo Retreat", "Pearl Bay House",
    "Cloud Nine Villa", "Ivory Tower Flat", "Golden Sands House", "Maple Leaf Lodge",
    "Silver Oak Apartment", "Jasmine Court", "Orchid Valley Home", "Pine Crest Cabin",
    "Sapphire Suite", "Emerald Heights", "Diamond View Flat", "Crystal Clear Studio",
    "Moonlight Terrace", "Starlight Penthouse", "Windmill Cottage", "Lighthouse Stay",
    "Harbor View Flat", "Cliff Edge Villa", "Meadow Run House", "Brookside Cottage",
    "Waterfall Lodge", "Sunset Point Villa", "Dawn Rise Flat", "Misty Hills House",
    "Echo Valley Home", "Coral Reef Suite", "Amber Palace Stay", "Cedar Wood Lodge",
    "Willow Creek Flat", "Rosewood Mansion", "Teak House", "Driftwood Cottage",
    "Sandstone Villa", "Granite Peak Lodge", "Marble Arch Flat", "Limestone Retreat",
    "Oakwood Estate", "Birch View Apartment", "Redwood Manor", "Walnut Grove Stay",
    "Magnolia House", "Tulip Garden Flat", "Lavender Fields Villa", "Sunflower Studio",
    "Daisy Chain Cottage", "Violet View Home",
]

VEHICLE_NAMES_PREFIX = [
    "Swift", "Royal", "Classic", "Premium", "Elite", "Urban", "Eco",
    "Turbo", "Rapid", "Smooth", "Power", "Easy", "Smart", "Quick", "Ace",
]
VEHICLE_MODELS = [
    "Dzire", "Innova", "Fortuner", "Creta", "Seltos", "XUV700", "Nexon",
    "Baleno", "Verna", "City", "Brezza", "Ertiga", "Thar", "Scorpio", "Harrier",
    "Activa", "Jupiter", "Access", "Dio", "Fascino", "TVS NTorq", "Pulsar",
    "Classic 350", "Duke 200", "Apache", "FZ", "R15", "Avenger", "Dominar",
    "Ather 450X", "Ola S1 Pro", "Chetak", "iQube",
]

COOK_NAMES = [
    "Chef Arjun", "Chef Priya", "Chef Ramesh", "Chef Lakshmi", "Chef Vikram",
    "Chef Ananya", "Chef Suresh", "Chef Meera", "Chef Karthik", "Chef Deepa",
    "Chef Rajesh", "Chef Sunita", "Chef Arun", "Chef Kavitha", "Chef Manoj",
    "Chef Divya", "Chef Sanjay", "Chef Nisha", "Chef Prakash", "Chef Asha",
    "Chef Venkat", "Chef Pooja", "Chef Ganesh", "Chef Radha", "Chef Mohan",
    "Chef Anjali", "Chef Ravi", "Chef Swati", "Chef Ajay", "Chef Bhavna",
    "Chef Dinesh", "Chef Geeta", "Chef Hari", "Chef Indira", "Chef Jayesh",
    "Chef Kamala", "Chef Lalit", "Chef Maya", "Chef Naveen", "Chef Padma",
    "Chef Rohit", "Chef Seema", "Chef Tarun", "Chef Uma", "Chef Vishal",
    "Chef Yamini", "Chef Ashok", "Chef Chitra", "Chef Gopal", "Chef Hema",
    "Chef Kishore", "Chef Lata", "Chef Murali", "Chef Neha", "Chef Om",
    "Chef Parul", "Chef Rakesh", "Chef Saroj", "Chef Tushar", "Chef Vandana",
]

CUISINES = ["North Indian", "South Indian", "Chinese", "Italian", "Thai",
            "Continental", "Mughlai", "Bengali", "Rajasthani", "Goan",
            "Kerala", "Street Food", "Bakery", "Japanese", "Mexican"]
SPECIALTIES = ["Biryani", "Tandoori", "Dosa", "Pasta", "Sushi",
               "Desserts", "BBQ", "Seafood", "Vegan", "Thali",
               "Chaat", "Kebabs", "Curries", "Bread Making", "Chutneys"]
AMENITIES = ["wifi", "parking", "pool", "gym", "ac", "kitchen",
             "washer", "balcony", "garden", "bbq", "hot_tub",
             "ev_charging", "cctv", "elevator", "generator"]
VEHICLE_FEATURES = ["ac", "gps", "bluetooth", "backup_camera", "sunroof",
                    "leather_seats", "cruise_control", "keyless_entry",
                    "usb_charging", "airbags", "abs", "alloy_wheels"]


def _rand_loc():
    city, lat, lng = random.choice(INDIAN_LOCATIONS)
    lat += random.uniform(-0.05, 0.05)
    lng += random.uniform(-0.05, 0.05)
    return city, round(lat, 6), round(lng, 6)


def _generate_venues(owner_id: uuid.UUID, type_id: uuid.UUID, count: int) -> list[Resource]:
    resources = []
    for i in range(count):
        name = VENUE_NAMES[i % len(VENUE_NAMES)]
        if i >= len(VENUE_NAMES):
            name = f"{name} {i // len(VENUE_NAMES) + 1}"
        city, lat, lng = _rand_loc()
        prop_type = random.choice(["apartment", "house", "villa", "studio", "event_space"])
        bedrooms = random.randint(1, 5)
        resources.append(Resource(
            type_id=type_id,
            name=name,
            description=(
                f"Beautiful {prop_type} in {city}. "
                f"{bedrooms} bedrooms with modern amenities and stunning views."
            ),
            location_lat=lat,
            location_lng=lng,
            location_address=f"{random.randint(1, 999)} {city} Main Road, {city}",
            attributes={
                "property_type": prop_type,
                "bedrooms": bedrooms,
                "bathrooms": random.randint(1, bedrooms),
                "max_guests": bedrooms * 2 + random.randint(0, 2),
                "amenities": random.sample(AMENITIES, k=random.randint(3, 8)),
                "pet_friendly": random.choice([True, False]),
            },
            base_price=round(random.uniform(1500, 25000), 2),
            currency="INR",
            status="active",
            rating_avg=round(random.uniform(3.0, 5.0), 1),
            rating_count=random.randint(0, 150),
            owner_id=owner_id,
        ))
    return resources


def _generate_vehicles(owner_id: uuid.UUID, type_id: uuid.UUID, count: int) -> list[Resource]:
    resources = []
    for i in range(count):
        model = VEHICLE_MODELS[i % len(VEHICLE_MODELS)]
        prefix = VEHICLE_NAMES_PREFIX[i % len(VEHICLE_NAMES_PREFIX)]
        name = f"{prefix} {model}"
        if i >= len(VEHICLE_MODELS):
            name = f"{name} #{i // len(VEHICLE_MODELS) + 1}"
        city, lat, lng = _rand_loc()
        is_two_wheeler = model in ("Activa", "Jupiter", "Access", "Dio", "Fascino",
                                    "TVS NTorq", "Pulsar", "Classic 350", "Duke 200",
                                    "Apache", "FZ", "R15", "Avenger", "Dominar")
        is_ev = model in ("Ather 450X", "Ola S1 Pro", "Chetak", "iQube")
        if is_two_wheeler:
            vtype = random.choice(["bike", "scooter"])
            seats = 2
            fuel = "electric" if is_ev else "petrol"
        else:
            vtype = random.choice(["car", "van"]) if model in ("Innova", "Ertiga") else "car"
            seats = random.choice([5, 7]) if vtype == "van" else 5
            fuel = random.choice(["petrol", "diesel", "hybrid"])

        state_code = random.choice(["MH", "DL", "KA", "TN", "WB", "TS", "RJ", "GJ", "GA"])
        letters = random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=2)
        reg_num = (
            f"{state_code}-{random.randint(1, 99):02d}-"
            f"{''.join(letters)}-{random.randint(1000, 9999)}"
        )

        resources.append(Resource(
            type_id=type_id,
            name=name,
            description=f"{model} available for rent in {city}. Well maintained, {fuel} engine.",
            location_lat=lat,
            location_lng=lng,
            location_address=f"{city} Rental Hub, {city}",
            attributes={
                "vehicle_type": vtype,
                "vehicle_number": reg_num,
                "engine_number": f"ENG{uuid.uuid4().hex[:10].upper()}",
                "chassis_number": f"CHS{uuid.uuid4().hex[:12].upper()}",
                "year": random.randint(2019, 2025),
                "seats": seats,
                "fuel_type": fuel,
                "transmission": random.choice(["manual", "automatic"]),
                "features": random.sample(VEHICLE_FEATURES, k=random.randint(2, 6)),
            },
            base_price=round(
                random.uniform(200, 5000) if is_two_wheeler
                else random.uniform(1500, 15000), 2
            ),
            currency="INR",
            status="active",
            rating_avg=round(random.uniform(3.0, 5.0), 1),
            rating_count=random.randint(0, 80),
            owner_id=owner_id,
        ))
    return resources


def _generate_cooks(owner_id: uuid.UUID, type_id: uuid.UUID, count: int) -> list[Resource]:
    resources = []
    for i in range(count):
        name = COOK_NAMES[i % len(COOK_NAMES)]
        if i >= len(COOK_NAMES):
            name = f"{name} {i // len(COOK_NAMES) + 1}"
        city, lat, lng = _rand_loc()
        exp = random.randint(2, 25)
        resources.append(Resource(
            type_id=type_id,
            name=name,
            description=(
                f"Professional chef with {exp} years experience in {city}. "
                "Specializing in multiple cuisines."
            ),
            location_lat=lat,
            location_lng=lng,
            location_address=f"{city}",
            attributes={
                "cuisine_type": random.sample(CUISINES, k=random.randint(2, 5)),
                "experience_years": exp,
                "specialties": random.sample(SPECIALTIES, k=random.randint(2, 4)),
                "max_guests_served": random.choice([10, 15, 20, 25, 30, 50]),
                "brings_own_ingredients": random.choice([True, False]),
            },
            base_price=round(random.uniform(500, 5000), 2),
            currency="INR",
            status="active",
            rating_avg=round(random.uniform(3.5, 5.0), 1),
            rating_count=random.randint(0, 60),
            owner_id=owner_id,
        ))
    return resources


async def _ensure_tenant(session: AsyncSession) -> Tenant:
    result = await session.exec(select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG))
    tenant = result.first()
    if tenant:
        print(f"  Tenant '{DEMO_TENANT_SLUG}' already exists (id={tenant.id})")
        return tenant

    tenant_id = uuid.uuid4()
    schema_name = f"tenant_{str(tenant_id).replace('-', '_')}"
    tenant = Tenant(
        id=tenant_id,
        name=DEMO_TENANT_NAME,
        slug=DEMO_TENANT_SLUG,
        schema_name=schema_name,
        base_currency="INR",
        timezone="Asia/Kolkata",
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    print(f"  Created tenant '{DEMO_TENANT_SLUG}' (id={tenant.id})")

    await provision_tenant_schema(engine, session, str(tenant_id))
    print("  Provisioned tenant schema + default roles")
    return tenant


async def _ensure_user(
    session: AsyncSession, email: str, password: str, full_name: str, user_type: str, role_slug: str
) -> User:
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if user:
        print(f"  User '{email}' already exists")
        return user

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        user_type=user_type,
        is_active=True,
        is_verified=True,
        preferred_currency="INR",
    )
    session.add(user)
    await session.flush()

    result = await session.exec(select(Role).where(Role.slug == role_slug))
    role = result.first()
    if role:
        session.add(UserRole(user_id=user.id, role_id=role.id))

    await session.commit()
    await session.refresh(user)
    print(f"  Created user '{email}' (role={role_slug})")
    return user


async def _seed_resources(
    session: AsyncSession, tenant: Tenant, owner: User
) -> dict[str, uuid.UUID]:
    type_ids = {}

    for slug, tmpl in RESOURCE_TYPE_TEMPLATES.items():
        result = await session.exec(
            select(ResourceType).where(ResourceType.slug == slug)
        )
        rt = result.first()
        if rt:
            print(f"  ResourceType '{slug}' already exists")
            type_ids[slug] = rt.id
            continue

        rt = ResourceType(
            name=tmpl["name"],
            slug=tmpl["slug"],
            icon=tmpl.get("icon"),
            description=tmpl.get("description"),
            availability_model=tmpl["availability_model"],
            pricing_model=tmpl["pricing_model"],
            attribute_schema=tmpl.get("attribute_schema"),
            slot_config=tmpl.get("slot_config"),
            pricing_config=tmpl.get("pricing_config"),
            cancellation_defaults=tmpl.get("cancellation_defaults"),
            role="primary" if slug == "venues" else "standalone",
        )
        session.add(rt)
        await session.commit()
        await session.refresh(rt)
        type_ids[slug] = rt.id
        print(f"  Created ResourceType '{slug}' (id={rt.id})")

        create_resource_type_index(
            str(tenant.id), rt.slug, rt.attribute_schema
        )

    existing = await session.exec(select(Resource).limit(1))
    if existing.first() is not None:
        print("  Resources already exist — skipping generation")
        return type_ids

    generators = {
        "venues": (_generate_venues, 70),
        "vehicles": (_generate_vehicles, 70),
        "cooks": (_generate_cooks, 60),
    }

    total = 0
    for slug, (gen_fn, count) in generators.items():
        resources = gen_fn(owner.id, type_ids[slug], count)
        for r in resources:
            session.add(r)
        await session.commit()

        for r in resources:
            await session.refresh(r)
            doc = build_document(
                r.id, r.name, r.description,
                r.location_lat, r.location_lng, r.location_address,
                r.attributes, r.base_price, r.currency,
                r.status, r.rating_avg, r.rating_count,
                slug, r.created_at,
            )
            sync_resource(str(tenant.id), slug, doc)

        total += len(resources)
        print(f"  Created {len(resources)} {slug} resources")

    print(f"  Total: {total} resources synced to Meilisearch")
    return type_ids


async def seed(reset: bool = False) -> None:
    print("\n=== RentManager Seed ===\n")

    async with async_session_factory() as session:
        if reset:
            result = await session.exec(
                select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG)
            )
            tenant = result.first()
            if tenant:
                print(f"  Dropping schema {tenant.schema_name}...")
                await session.execute(text(f"DROP SCHEMA IF EXISTS {tenant.schema_name} CASCADE"))
                await session.execute(text(f"DELETE FROM tenants WHERE id = '{tenant.id}'"))
                await session.commit()
                print("  Dropped. Re-creating...")

    async with async_session_factory() as session:
        tenant = await _ensure_tenant(session)

    schema = tenant.schema_name
    async with async_session_factory() as session:
        await session.execute(text(f"SET search_path TO {schema}, public"))

        await _ensure_user(
            session, ADMIN_EMAIL, ADMIN_PASSWORD,
            "Demo Admin", "admin", "admin",
        )
        await _ensure_user(
            session, CUSTOMER_EMAIL, CUSTOMER_PASSWORD,
            "Demo Customer", "customer", "customer",
        )
        lister = await _ensure_user(
            session, LISTER_EMAIL, LISTER_PASSWORD,
            "Demo Lister", "lister", "lister",
        )

        type_ids = await _seed_resources(session, tenant, lister)

        await session.execute(text("SET search_path TO public"))

    print(f"""
=== Seed Complete ===

Tenant:   {tenant.name} (slug: {tenant.slug})
Schema:   {schema}

Users:
  admin@demo.com     / admin123     (admin)
  customer@demo.com  / customer123  (customer)
  lister@demo.com    / lister123    (lister)

Resource Types:
  venues    → {type_ids.get('venues', 'exists')}
  vehicles  → {type_ids.get('vehicles', 'exists')}
  cooks     → {type_ids.get('cooks', 'exists')}

Access:
  http://localhost:3000/t/demo/login
  http://localhost:8000/api/docs
""")


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    asyncio.run(seed(reset=reset))
