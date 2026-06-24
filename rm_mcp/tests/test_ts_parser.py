from pathlib import Path


def test_parse_pages():
    from rm_mcp.indexer.ts_parser import parse_pages
    from rm_mcp.config import FRONTEND_DIR, PROJECT_ROOT

    pages = parse_pages(FRONTEND_DIR, PROJECT_ROOT)

    assert len(pages) > 0
    admin_bookings = next((p for p in pages if p["route"] == "/admin/bookings"), None)
    assert admin_bookings is not None
    assert "page.tsx" in admin_bookings["file"]


def test_parse_hooks():
    from rm_mcp.indexer.ts_parser import parse_hooks
    from rm_mcp.config import FRONTEND_DIR, PROJECT_ROOT

    hooks = parse_hooks(FRONTEND_DIR, PROJECT_ROOT)

    assert len(hooks) > 0
    booking_flow = next((h for h in hooks if h["name"] == "useBookingFlow"), None)
    assert booking_flow is not None
    assert len(booking_flow["api_calls"]) > 0


def test_parse_stores():
    from rm_mcp.indexer.ts_parser import parse_stores
    from rm_mcp.config import FRONTEND_DIR, PROJECT_ROOT

    stores = parse_stores(FRONTEND_DIR, PROJECT_ROOT)

    assert len(stores) > 0
    auth_store = next((s for s in stores if "auth" in s["name"]), None)
    assert auth_store is not None


def test_parse_hook_api_calls_extract_methods():
    from rm_mcp.indexer.ts_parser import extract_api_calls
    from rm_mcp.config import FRONTEND_DIR

    hook_file = FRONTEND_DIR / "hooks" / "use-booking-flow.ts"
    source = hook_file.read_text()
    calls = extract_api_calls(source)

    post_calls = [c for c in calls if c["method"] == "POST"]
    assert len(post_calls) > 0
    assert any("/bookings" in c["path"] for c in post_calls)


def test_parse_frontend_full():
    from rm_mcp.indexer.ts_parser import parse_frontend
    from rm_mcp.config import FRONTEND_DIR, PROJECT_ROOT

    result = parse_frontend(FRONTEND_DIR, PROJECT_ROOT)

    assert len(result["pages"]) > 0
    assert len(result["hooks"]) > 0
    assert len(result["stores"]) > 0
