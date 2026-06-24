# rm_mcp/server.py
import json

from fastmcp import FastMCP

from rm_mcp.config import INDEX_PATH
from rm_mcp.docs import get_doc as _get_doc, list_docs, search_docs
from rm_mcp.indexer.pipeline import load_index
from rm_mcp.query import (
    find_symbol as _find_symbol,
    get_schema as _get_schema,
    list_pages as _list_pages,
    list_routes as _list_routes,
    query_index,
    trace_flow as _trace_flow,
)

mcp = FastMCP(
    name="rm-mcp",
    version="1.0.0",
)


def _ensure_index() -> dict:
    index = load_index()
    if not index:
        from rm_mcp.indexer.pipeline import run_reindex
        run_reindex(quiet=True)
        index = load_index()
    if not index:
        raise RuntimeError("Failed to build index")
    return index


@mcp.tool()
def trace_flow(from_identifier: str) -> str:
    """Trace the full path from a frontend page or hook through API calls to backend service and database model.

    Args:
        from_identifier: Page route (e.g. "admin/bookings"), hook name (e.g. "useBookingFlow"), or API path (e.g. "/bookings")
    """
    index = _ensure_index()
    traces = _trace_flow(index, from_identifier)
    if not traces:
        return f"No traces found for '{from_identifier}'"
    return json.dumps(traces, indent=2)


@mcp.tool()
def list_routes(module: str | None = None) -> str:
    """List all backend API routes with methods, handlers, and auth requirements.

    Args:
        module: Optional filter by module name (e.g. "bookings", "payments"). Returns all routes if omitted.
    """
    index = _ensure_index()
    routes = _list_routes(index, module)
    if not routes:
        return f"No routes found" + (f" for module '{module}'" if module else "")
    return json.dumps(routes, indent=2)


@mcp.tool()
def list_pages(area: str | None = None) -> str:
    """List all frontend pages with their hooks and API calls.

    Args:
        area: Optional filter by area (e.g. "admin", "public", "superadmin"). Returns all pages if omitted.
    """
    index = _ensure_index()
    pages = _list_pages(index, area)
    if not pages:
        return f"No pages found" + (f" for area '{area}'" if area else "")
    return json.dumps(pages, indent=2)


@mcp.tool()
def find_symbol(name: str) -> str:
    """Find a function, class, model, hook, or component by name across the entire codebase.

    Args:
        name: Symbol name to search for (e.g. "create_booking", "Booking", "useBookingFlow")
    """
    index = _ensure_index()
    results = _find_symbol(index, name)
    if not results:
        return f"No symbol found matching '{name}'"
    return json.dumps(results, indent=2)


@mcp.tool()
def query(q: str) -> str:
    """Fuzzy search across all indexed items — routes, services, models, schemas, tasks, pages, hooks.

    Args:
        q: Search query (e.g. "payment processing", "booking confirm", "auth")
    """
    index = _ensure_index()
    results = query_index(index, q)

    # Also search docs; cap doc scores to match index scoring scale (len of terms)
    terms = q.split()
    max_score = len(terms) if terms else 1
    doc_results = search_docs(q)
    for doc in doc_results:
        capped_score = min(doc["score"], max_score)
        results.append({"score": capped_score, "type": "doc", "item": doc})

    results.sort(key=lambda r: r["score"], reverse=True)
    if not results:
        return f"No results found for '{q}'"
    return json.dumps(results[:20], indent=2)


@mcp.tool()
def get_schema(name: str) -> str:
    """Get detailed schema for a Pydantic model or SQLAlchemy model — fields, types, relationships.

    Args:
        name: Model or schema name (e.g. "Booking", "BookingCreate", "User")
    """
    index = _ensure_index()
    result = _get_schema(index, name)
    if not result:
        return f"No schema found for '{name}'"
    return json.dumps(result, indent=2)


@mcp.tool()
def get_doc(topic: str) -> str:
    """Get a knowledge document by topic name.

    Args:
        topic: Document topic (e.g. "architecture-overview", "booking-state-machine", "auth-flow")
    """
    content = _get_doc(topic)
    if not content:
        available = list_docs()
        topics = [d["topic"] for d in available]
        return f"No doc found for '{topic}'. Available: {', '.join(topics)}"
    return content


@mcp.tool()
def overview() -> str:
    """Get a project overview: module counts, route counts, page counts, index freshness."""
    index = _ensure_index()
    backend = index.get("backend", {})
    frontend = index.get("frontend", {})
    links = index.get("links", [])
    docs = list_docs()

    summary = {
        "indexed_at": index.get("indexed_at"),
        "backend": {
            "routes": len(backend.get("routes", [])),
            "services": len(backend.get("services", [])),
            "models": len(backend.get("models", [])),
            "schemas": len(backend.get("schemas", [])),
            "celery_tasks": len(backend.get("tasks", [])),
        },
        "frontend": {
            "pages": len(frontend.get("pages", [])),
            "hooks": len(frontend.get("hooks", [])),
            "stores": len(frontend.get("stores", [])),
            "components": len(frontend.get("components", [])),
        },
        "cross_stack_links": len(links),
        "knowledge_docs": len(docs),
        "doc_topics": [d["topic"] for d in docs],
    }
    return json.dumps(summary, indent=2)


# --- Resources ---

@mcp.resource("rm://overview")
def resource_overview() -> str:
    """Project summary — module list, route count, page count."""
    return overview()


@mcp.resource("rm://routes")
def resource_routes() -> str:
    """Complete API route table."""
    return list_routes()


@mcp.resource("rm://pages")
def resource_pages() -> str:
    """Complete page → endpoint mapping."""
    return list_pages()


@mcp.resource("rm://docs/{topic}")
def resource_doc(topic: str) -> str:
    """Individual knowledge doc by topic name."""
    return get_doc(topic)


@mcp.resource("rm://index-status")
def resource_index_status() -> str:
    """Index age, file counts, staleness."""
    index = _ensure_index()
    return json.dumps({
        "indexed_at": index.get("indexed_at"),
        "version": index.get("version"),
        "index_path": str(INDEX_PATH),
    }, indent=2)


def serve():
    mcp.run(transport="stdio")
