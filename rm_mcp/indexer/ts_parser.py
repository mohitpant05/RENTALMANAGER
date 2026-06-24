import re
from pathlib import Path


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _route_from_page_path(filepath: Path, frontend_dir: Path) -> str:
    """Convert file path to Next.js route.

    frontend/src/app/admin/bookings/page.tsx -> /admin/bookings
    frontend/src/app/(public)/resources/[id]/page.tsx -> /(public)/resources/[id]
    """
    rel = filepath.relative_to(frontend_dir / "app")
    parts = list(rel.parts[:-1])  # drop page.tsx
    if not parts:
        return "/"
    return "/" + "/".join(parts)


def extract_api_calls(source: str) -> list[dict]:
    """Extract api.get/post/put/delete calls using regex.

    Matches patterns like:
      api.post<Type>("/bookings", payload)
      api.get(`/resources/${id}`)
      api.post<void>(`/resources/${resourceId}/availability/release`, ...)

    Handles both single-line and multi-line call patterns where the URL
    is on the next line after the method call.
    """
    calls = []

    # First pass: single-line patterns where method and URL are on the same line
    single_line_pattern = r'api\.(get|post|put|delete|patch)\s*(?:<[^>]*>)?\s*\(\s*[`"\']([^`"\']+)[`"\']'

    for i, line in enumerate(source.splitlines(), 1):
        for match in re.finditer(single_line_pattern, line):
            method = match.group(1).upper()
            path = match.group(2)
            # Normalize template literal variables
            path = re.sub(r'\$\{[^}]+\}', '*', path)
            calls.append({"method": method, "path": path, "line": i})

    # Second pass: multi-line patterns where URL is on the line after the method
    # e.g.:
    #   api.post<Type>(
    #     `/resources/${id}/check`,
    multi_line_pattern = r'api\.(get|post|put|delete|patch)\s*(?:<[^>]*>)?\s*\(\s*\n\s*[`"\']([^`"\']+)[`"\']'

    for match in re.finditer(multi_line_pattern, source, re.MULTILINE):
        method = match.group(1).upper()
        path = match.group(2)
        path = re.sub(r'\$\{[^}]+\}', '*', path)
        # Find line number by counting newlines before match start
        line_num = source[:match.start()].count('\n') + 1
        # Avoid duplicates (same method+path that was already found)
        already_found = any(
            c["method"] == method
            and c["path"] == path
            and abs(c["line"] - line_num) <= 2
            for c in calls
        )
        if not already_found:
            calls.append({"method": method, "path": path, "line": line_num})

    return calls


def extract_imports(source: str) -> list[dict]:
    """Extract import statements to find hook and component usage."""
    pattern = r'import\s+(?:{([^}]+)}|(\w+))\s+from\s+["\']([^"\']+)["\']'
    imports = []
    for match in re.finditer(pattern, source):
        named = match.group(1)
        default = match.group(2)
        module = match.group(3)
        if named:
            names = [n.strip().split(" as ")[0].strip() for n in named.split(",")]
            for name in names:
                if name:
                    imports.append({"name": name, "module": module})
        if default:
            imports.append({"name": default, "module": module})
    return imports


def parse_pages(frontend_dir: Path, project_root: Path) -> list[dict]:
    pages = []
    app_dir = frontend_dir / "app"

    for page_file in app_dir.rglob("page.tsx"):
        route = _route_from_page_path(page_file, frontend_dir)
        source = page_file.read_text()

        imports = extract_imports(source)
        hooks_used = [
            imp["name"] for imp in imports
            if imp["name"].startswith("use") and imp["name"][3:4].isupper()
        ]
        components_used = [
            imp["name"] for imp in imports
            if imp["name"][0:1].isupper()
            and not imp["name"].startswith("use")
            and imp["module"].startswith("@/components")
        ]
        api_calls = extract_api_calls(source)

        pages.append({
            "route": route,
            "file": _rel(page_file, project_root),
            "hooks_used": hooks_used,
            "components_used": components_used,
            "api_calls": api_calls,
        })

    return pages


def parse_hooks(frontend_dir: Path, project_root: Path) -> list[dict]:
    hooks = []
    hooks_dir = frontend_dir / "hooks"

    if not hooks_dir.exists():
        return hooks

    for hook_file in hooks_dir.glob("use-*.ts"):
        source = hook_file.read_text()

        # Derive hook name: use-booking-flow.ts -> useBookingFlow
        stem = hook_file.stem  # use-booking-flow
        parts = stem.split("-")
        hook_name = parts[0] + "".join(p.capitalize() for p in parts[1:])

        api_calls = extract_api_calls(source)
        imports = extract_imports(source)

        stores_used = [
            imp["name"] for imp in imports
            if "store" in imp["module"].lower()
        ]

        hooks.append({
            "name": hook_name,
            "file": _rel(hook_file, project_root),
            "api_calls": api_calls,
            "stores_used": stores_used,
        })

    return hooks


def parse_stores(frontend_dir: Path, project_root: Path) -> list[dict]:
    stores = []
    lib_dir = frontend_dir / "lib"

    if not lib_dir.exists():
        return stores

    for store_file in lib_dir.glob("*-store.ts"):
        source = store_file.read_text()

        # Derive store name: auth-store.ts -> authStore
        stem = store_file.stem  # auth-store
        parts = stem.split("-")
        store_name = parts[0] + "".join(p.capitalize() for p in parts[1:])

        # Extract exported function/interface names
        exports = re.findall(r'export\s+(?:function|const|interface|type)\s+(\w+)', source)

        stores.append({
            "name": store_name,
            "file": _rel(store_file, project_root),
            "exports": exports,
        })

    return stores


def parse_components(frontend_dir: Path, project_root: Path) -> list[dict]:
    components = []
    comp_dir = frontend_dir / "components"

    if not comp_dir.exists():
        return components

    for tsx_file in comp_dir.rglob("*.tsx"):
        if tsx_file.name == "page.tsx" or tsx_file.name == "layout.tsx":
            continue

        source = tsx_file.read_text()
        exports = re.findall(r'export\s+(?:default\s+)?function\s+(\w+)', source)
        if not exports:
            exports = re.findall(r'export\s+const\s+(\w+)', source)

        imports = extract_imports(source)
        hooks_used = [
            imp["name"] for imp in imports
            if imp["name"].startswith("use") and imp["name"][3:4].isupper()
        ]

        for export_name in exports:
            components.append({
                "name": export_name,
                "file": _rel(tsx_file, project_root),
                "hooks_used": hooks_used,
            })

    return components


def parse_frontend(frontend_dir: Path, project_root: Path) -> dict:
    return {
        "pages": parse_pages(frontend_dir, project_root),
        "hooks": parse_hooks(frontend_dir, project_root),
        "stores": parse_stores(frontend_dir, project_root),
        "components": parse_components(frontend_dir, project_root),
    }
