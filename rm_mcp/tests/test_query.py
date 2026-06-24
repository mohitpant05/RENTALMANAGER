"""Tests for the query engine (rm_mcp/query.py)."""


def _get_index():
    from rm_mcp.indexer.pipeline import load_index, run_reindex
    from rm_mcp.config import INDEX_PATH
    if not INDEX_PATH.exists():
        run_reindex(quiet=True)
    return load_index()


def test_trace_flow():
    from rm_mcp.query import trace_flow
    index = _get_index()
    traces = trace_flow(index, "admin/bookings")
    assert len(traces) > 0
    trace = traces[0]
    assert "page" in trace
    assert "api_path" in trace


def test_list_routes_all():
    from rm_mcp.query import list_routes
    index = _get_index()
    routes = list_routes(index, module=None)
    assert len(routes) > 0


def test_list_routes_filtered():
    from rm_mcp.query import list_routes
    index = _get_index()
    routes = list_routes(index, module="bookings")
    assert len(routes) > 0
    assert all("booking" in r["path"].lower() for r in routes)


def test_list_pages():
    from rm_mcp.query import list_pages
    index = _get_index()
    pages = list_pages(index, area="admin")
    assert len(pages) > 0
    assert all("/admin" in p["route"] for p in pages)


def test_find_symbol():
    from rm_mcp.query import find_symbol
    index = _get_index()
    results = find_symbol(index, "Booking")
    assert len(results) > 0
    types_found = {r["type"] for r in results}
    assert "model" in types_found or "schema" in types_found


def test_query_index():
    from rm_mcp.query import query_index
    index = _get_index()
    results = query_index(index, "payment")
    assert len(results) > 0


def test_get_schema_model():
    from rm_mcp.query import get_schema
    index = _get_index()
    result = get_schema(index, "Booking")
    assert result is not None
    assert result["name"] == "Booking"
    assert "columns" in result or "fields" in result
