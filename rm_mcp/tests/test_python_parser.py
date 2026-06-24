from pathlib import Path


def test_parse_routes_from_bookings_router():
    from rm_mcp.indexer.python_parser import parse_router_file
    from rm_mcp.config import BACKEND_DIR, PROJECT_ROOT

    router_file = BACKEND_DIR / "domains" / "bookings" / "router.py"
    routes = parse_router_file(router_file, PROJECT_ROOT)

    assert len(routes) > 0

    post_route = next((r for r in routes if r["handler"] == "create_booking_endpoint"), None)
    assert post_route is not None
    assert post_route["method"] == "POST"
    assert post_route["path"] == "/api/bookings"
    assert "get_current_user" in post_route["dependencies"]


def test_parse_models_from_bookings():
    from rm_mcp.indexer.python_parser import parse_model_file
    from rm_mcp.config import BACKEND_DIR, PROJECT_ROOT

    model_file = BACKEND_DIR / "domains" / "bookings" / "models.py"
    models = parse_model_file(model_file, PROJECT_ROOT)

    booking = next((m for m in models if m["name"] == "Booking"), None)
    assert booking is not None
    assert booking["table"] == "bookings"
    assert any(c["name"] == "status" for c in booking["columns"])


def test_parse_schemas_from_bookings():
    from rm_mcp.indexer.python_parser import parse_schema_file
    from rm_mcp.config import BACKEND_DIR, PROJECT_ROOT

    schema_file = BACKEND_DIR / "domains" / "bookings" / "schemas.py"
    schemas = parse_schema_file(schema_file, PROJECT_ROOT)

    create_schema = next((s for s in schemas if s["name"] == "BookingCreate"), None)
    assert create_schema is not None
    assert any(f["name"] == "resource_id" for f in create_schema["fields"])


def test_parse_services_from_bookings():
    from rm_mcp.indexer.python_parser import parse_service_file
    from rm_mcp.config import BACKEND_DIR, PROJECT_ROOT

    service_file = BACKEND_DIR / "domains" / "bookings" / "service.py"
    services = parse_service_file(service_file, PROJECT_ROOT)

    create_svc = next((s for s in services if s["name"] == "create_booking"), None)
    assert create_svc is not None
    assert len(create_svc["params"]) > 0


def test_parse_celery_tasks():
    from rm_mcp.indexer.python_parser import parse_celery_tasks
    from rm_mcp.config import PROJECT_ROOT

    celery_file = PROJECT_ROOT / "backend" / "app" / "celery_app.py"
    tasks = parse_celery_tasks(celery_file, PROJECT_ROOT)

    assert len(tasks) > 0
    cleanup = next((t for t in tasks if "cleanup" in t["name"]), None)
    assert cleanup is not None


def test_parse_backend_full():
    from rm_mcp.indexer.python_parser import parse_backend
    from rm_mcp.config import BACKEND_DIR, PROJECT_ROOT

    result = parse_backend(BACKEND_DIR, PROJECT_ROOT)

    assert len(result["routes"]) > 0
    assert len(result["models"]) > 0
    assert len(result["schemas"]) > 0
    assert len(result["services"]) > 0
    assert len(result["tasks"]) > 0
