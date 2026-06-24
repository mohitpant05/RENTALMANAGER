import json


def setup_module():
    from rm_mcp.indexer.pipeline import run_reindex
    run_reindex(quiet=True)


def test_overview_has_all_sections():
    from rm_mcp.server import overview
    result = json.loads(overview())
    assert result["backend"]["routes"] > 0
    assert result["backend"]["models"] > 0
    assert result["frontend"]["pages"] > 0
    assert result["frontend"]["hooks"] > 0
    assert result["knowledge_docs"] > 0


def test_trace_booking_flow():
    from rm_mcp.server import trace_flow
    result = json.loads(trace_flow("admin/bookings"))
    assert len(result) > 0
    link = result[0]
    assert link["page"] is not None
    assert link["api_path"] is not None


def test_find_booking_model():
    from rm_mcp.server import find_symbol
    result = json.loads(find_symbol("Booking"))
    types = {r["type"] for r in result}
    assert "model" in types


def test_get_booking_schema():
    from rm_mcp.server import get_schema
    result = json.loads(get_schema("Booking"))
    assert result["name"] == "Booking"
    assert len(result["columns"]) > 0


def test_query_payment():
    from rm_mcp.server import query
    result = json.loads(query("payment"))
    assert len(result) > 0


def test_get_architecture_doc():
    from rm_mcp.server import get_doc
    result = get_doc("architecture-overview")
    assert len(result) > 100


def test_list_admin_pages():
    from rm_mcp.server import list_pages
    result = json.loads(list_pages("admin"))
    assert len(result) > 5


def test_list_booking_routes():
    from rm_mcp.server import list_routes
    result = json.loads(list_routes("bookings"))
    assert len(result) > 0
    methods = {r["method"] for r in result}
    assert "POST" in methods
    assert "GET" in methods
