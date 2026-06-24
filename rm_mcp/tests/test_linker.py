def test_match_api_path():
    from rm_mcp.indexer.linker import match_api_path

    assert match_api_path("/bookings", "/api/bookings") is True
    assert match_api_path("/resources/*/availability/check", "/api/resources/{resource_id}/availability/check") is True
    assert match_api_path("/bookings", "/api/payments") is False


def test_build_links():
    from rm_mcp.indexer.linker import build_links

    backend = {
        "routes": [
            {"method": "POST", "path": "/api/bookings", "handler": "create_booking_endpoint",
             "file": "backend/app/domains/bookings/router.py", "line": 33,
             "service_calls": ["create_booking"], "auth_required": True, "dependencies": []},
        ],
        "services": [
            {"name": "create_booking", "module": "bookings",
             "file": "backend/app/domains/bookings/service.py", "line": 36,
             "params": [], "models_used": ["Booking"], "calls": [], "is_async": True},
        ],
        "models": [{"name": "Booking", "table": "bookings", "file": "backend/app/domains/bookings/models.py", "line": 11, "columns": [], "relationships": []}],
        "schemas": [],
        "tasks": [],
    }
    frontend = {
        "pages": [
            {"route": "/admin/bookings", "file": "frontend/src/app/admin/bookings/page.tsx",
             "hooks_used": ["useBookingFlow"], "components_used": [], "api_calls": []},
        ],
        "hooks": [
            {"name": "useBookingFlow", "file": "frontend/src/hooks/use-booking-flow.ts",
             "api_calls": [{"method": "POST", "path": "/bookings", "line": 274}],
             "stores_used": []},
        ],
        "stores": [],
        "components": [],
    }

    links = build_links(backend, frontend)
    assert len(links) > 0
    link = links[0]
    assert link["page"] == "/admin/bookings"
    assert link["hook"] == "useBookingFlow"
    assert "bookings" in link["api_path"].lower()
    assert "create_booking" in link["handler"]
