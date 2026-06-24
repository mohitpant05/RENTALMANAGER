import re


def _normalize_path(path: str) -> str:
    """Normalize API path for comparison.

    /api/bookings/{id}/confirm -> bookings/*/confirm
    /resources/*/availability/check -> resources/*/availability/check
    """
    path = re.sub(r'^/api/?', '', path)
    path = re.sub(r'\{[^}]+\}', '*', path)
    path = path.strip('/')
    return path


def match_api_path(frontend_path: str, backend_path: str) -> bool:
    front_norm = _normalize_path(frontend_path)
    back_norm = _normalize_path(backend_path)

    if front_norm == back_norm:
        return True

    # Try matching with wildcard expansion
    front_parts = front_norm.split('/')
    back_parts = back_norm.split('/')

    if len(front_parts) != len(back_parts):
        return False

    for fp, bp in zip(front_parts, back_parts):
        if fp == '*' or bp == '*':
            continue
        if fp != bp:
            return False

    return True


def _find_service_for_handler(handler_name: str, service_calls: list[str], services: list[dict]) -> dict | None:
    for call_name in service_calls:
        for svc in services:
            if svc["name"] == call_name:
                return svc
    return None


def _find_model_for_service(service: dict) -> str | None:
    for model_name in service.get("models_used", []):
        return model_name
    return None


def build_links(backend: dict, frontend: dict) -> list[dict]:
    links = []

    # Build page -> hook mapping
    page_hooks = {}
    for page in frontend["pages"]:
        for hook_name in page["hooks_used"]:
            page_hooks.setdefault(hook_name, []).append(page)

    # For each hook's API call, find the matching backend route
    for hook in frontend["hooks"]:
        for api_call in hook["api_calls"]:
            for route in backend["routes"]:
                if api_call["method"] != route["method"]:
                    continue
                if not match_api_path(api_call["path"], route["path"]):
                    continue

                service = _find_service_for_handler(
                    route["handler"], route["service_calls"], backend["services"]
                )
                model_name = _find_model_for_service(service) if service else None

                pages_using_hook = page_hooks.get(hook["name"], [])
                for page in pages_using_hook:
                    links.append({
                        "page": page["route"],
                        "hook": hook["name"],
                        "api_path": f"{route['method']} {route['path']}",
                        "handler": f"{route['file'].split('/')[-2]}.router.{route['handler']}",
                        "service": f"{service['module']}.service.{service['name']}" if service else None,
                        "model": model_name,
                    })

    # Also check pages with direct API calls (no hook)
    for page in frontend["pages"]:
        for api_call in page["api_calls"]:
            for route in backend["routes"]:
                if api_call["method"] != route["method"]:
                    continue
                if not match_api_path(api_call["path"], route["path"]):
                    continue

                service = _find_service_for_handler(
                    route["handler"], route["service_calls"], backend["services"]
                )
                model_name = _find_model_for_service(service) if service else None

                links.append({
                    "page": page["route"],
                    "hook": None,
                    "api_path": f"{route['method']} {route['path']}",
                    "handler": f"{route['file'].split('/')[-2]}.router.{route['handler']}",
                    "service": f"{service['module']}.service.{service['name']}" if service else None,
                    "model": model_name,
                })

    return links
