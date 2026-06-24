"""
Query engine for searching and tracing the RM index.
Provides search, filter, and trace logic over the index. Used by MCP tools.
"""


def trace_flow(index: dict, from_page: str) -> list[dict]:
    """Trace full path from page to backend for matching links."""
    links = index.get("links", [])
    matches = []

    from_page = from_page.strip("/")
    for link in links:
        page_clean = link["page"].strip("/")
        if from_page in page_clean or page_clean in from_page:
            matches.append(link)

    if not matches:
        # Try matching by hook name
        for link in links:
            if link.get("hook") and from_page.lower() in link["hook"].lower():
                matches.append(link)

    if not matches:
        # Try matching by route path
        for link in links:
            if from_page.lower() in link.get("api_path", "").lower():
                matches.append(link)

    return matches


def list_routes(index: dict, module: str | None = None) -> list[dict]:
    """List backend routes, optionally filtered by module name."""
    routes = index.get("backend", {}).get("routes", [])
    if module:
        module_lower = module.lower()
        routes = [r for r in routes if module_lower in r["path"].lower() or module_lower in r["file"].lower()]
    return routes


def list_pages(index: dict, area: str | None = None) -> list[dict]:
    """List frontend pages, optionally filtered by area (e.g. 'admin').

    Matching is path-segment aware: area='admin' matches /admin and /admin/foo
    but not /superadmin.
    """
    pages = index.get("frontend", {}).get("pages", [])
    if area:
        area_lower = area.lower()
        segment = f"/{area_lower}"
        pages = [
            p for p in pages
            if p["route"].lower() == segment
            or p["route"].lower().startswith(segment + "/")
        ]
    return pages


def find_symbol(index: dict, name: str) -> list[dict]:
    """Find any indexed symbol (route handler, service, model, schema, task, hook, page, store) by name."""
    results = []
    name_lower = name.lower()
    backend = index.get("backend", {})
    frontend = index.get("frontend", {})

    for route in backend.get("routes", []):
        if name_lower in route["handler"].lower():
            results.append({**route, "type": "route"})

    for svc in backend.get("services", []):
        if name_lower in svc["name"].lower():
            results.append({**svc, "type": "service"})

    for model in backend.get("models", []):
        if name_lower in model["name"].lower():
            results.append({**model, "type": "model"})

    for schema in backend.get("schemas", []):
        if name_lower in schema["name"].lower():
            results.append({**schema, "type": "schema"})

    for task in backend.get("tasks", []):
        if name_lower in task["name"].lower() or name_lower in task.get("function", "").lower():
            results.append({**task, "type": "task"})

    for hook in frontend.get("hooks", []):
        if name_lower in hook["name"].lower():
            results.append({**hook, "type": "hook"})

    for page in frontend.get("pages", []):
        if name_lower in page["route"].lower() or name_lower in page["file"].lower():
            results.append({**page, "type": "page"})

    for store in frontend.get("stores", []):
        if name_lower in store["name"].lower():
            results.append({**store, "type": "store"})

    return results


def query_index(index: dict, q: str) -> list[dict]:
    """Fuzzy search across all indexed items and knowledge docs."""
    results = []
    q_lower = q.lower()
    terms = q_lower.split()

    def score(text: str) -> int:
        text_lower = text.lower()
        return sum(1 for t in terms if t in text_lower)

    backend = index.get("backend", {})
    frontend = index.get("frontend", {})

    for route in backend.get("routes", []):
        s = score(f"{route['path']} {route['handler']} {route['file']}")
        if s > 0:
            results.append({"score": s, "type": "route", "item": route})

    for svc in backend.get("services", []):
        s = score(f"{svc['name']} {svc['module']} {svc['file']}")
        if s > 0:
            results.append({"score": s, "type": "service", "item": svc})

    for model in backend.get("models", []):
        s = score(f"{model['name']} {model['table']} {model['file']}")
        if s > 0:
            results.append({"score": s, "type": "model", "item": model})

    for schema in backend.get("schemas", []):
        s = score(f"{schema['name']} {schema['file']}")
        if s > 0:
            results.append({"score": s, "type": "schema", "item": schema})

    for task in backend.get("tasks", []):
        s = score(f"{task['name']} {task.get('function', '')} {task['file']}")
        if s > 0:
            results.append({"score": s, "type": "task", "item": task})

    for page in frontend.get("pages", []):
        s = score(f"{page['route']} {page['file']}")
        if s > 0:
            results.append({"score": s, "type": "page", "item": page})

    for hook in frontend.get("hooks", []):
        s = score(f"{hook['name']} {hook['file']}")
        if s > 0:
            results.append({"score": s, "type": "hook", "item": hook})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:20]


def get_schema(index: dict, name: str) -> dict | None:
    """Get full schema/model definition by exact name (case-insensitive)."""
    name_lower = name.lower()

    for model in index.get("backend", {}).get("models", []):
        if model["name"].lower() == name_lower:
            return {**model, "kind": "model"}

    for schema in index.get("backend", {}).get("schemas", []):
        if schema["name"].lower() == name_lower:
            return {**schema, "kind": "schema"}

    return None
