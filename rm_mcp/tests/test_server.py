import json


def test_server_has_tools():
    from rm_mcp.server import mcp

    tools = mcp._tool_manager._tools
    tool_names = set(tools.keys())

    expected = {"trace_flow", "list_routes", "list_pages", "find_symbol", "query", "get_schema", "get_doc", "overview"}
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


def test_overview_tool():
    from rm_mcp.server import mcp
    import asyncio

    # Ensure index exists
    from rm_mcp.indexer.pipeline import run_reindex
    from rm_mcp.config import INDEX_PATH
    if not INDEX_PATH.exists():
        run_reindex(quiet=True)

    tool_fn = mcp._tool_manager._tools["overview"].fn
    result = asyncio.run(tool_fn()) if asyncio.iscoroutinefunction(tool_fn) else tool_fn()
    assert "routes" in str(result).lower() or "pages" in str(result).lower()
