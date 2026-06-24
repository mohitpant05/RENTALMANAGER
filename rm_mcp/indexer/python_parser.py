import ast
from pathlib import Path


def _rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def parse_router_file(filepath: Path, project_root: Path) -> list[dict]:
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    routes = []

    # Collect all APIRouter instances and their prefixes
    # A file may have multiple APIRouter instances (e.g. resource_router, resource_type_router)
    router_prefixes: dict[str, str] = {}  # variable_name -> prefix

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    call = node.value
                    # Check if this is an APIRouter call
                    is_api_router = (
                        (isinstance(call.func, ast.Name) and call.func.id == "APIRouter")
                        or (isinstance(call.func, ast.Attribute) and call.func.attr == "APIRouter")
                    )
                    if is_api_router:
                        prefix = ""
                        for kw in call.keywords:
                            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                prefix = kw.value.value
                        router_prefixes[target.id] = prefix

    # Default prefix: use the first (or only) router prefix found
    # If none found, use empty string
    default_prefix = next(iter(router_prefixes.values()), "") if router_prefixes else ""

    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not isinstance(deco.func, ast.Attribute):
                continue
            method = deco.func.attr.upper()
            if method not in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                continue

            # Determine which router this decorator belongs to
            router_var = ""
            if isinstance(deco.func.value, ast.Name):
                router_var = deco.func.value.id

            prefix = router_prefixes.get(router_var, default_prefix)

            path_arg = ""
            if deco.args and isinstance(deco.args[0], ast.Constant):
                path_arg = deco.args[0].value

            full_path = prefix + path_arg

            deps = []
            # Depends() calls appear as default values in function args
            all_defaults = list(node.args.defaults) + [
                d for d in node.args.kw_defaults if d is not None
            ]
            for default in all_defaults:
                if default is None:
                    continue
                if isinstance(default, ast.Call) and isinstance(default.func, ast.Name):
                    if default.func.id == "Depends":
                        if default.args:
                            arg = default.args[0]
                            if isinstance(arg, ast.Name):
                                deps.append(arg.id)
                            elif isinstance(arg, ast.Call):
                                if isinstance(arg.func, ast.Name):
                                    deps.append(arg.func.id + "(...)")
                                elif isinstance(arg.func, ast.Attribute):
                                    deps.append(arg.func.attr + "(...)")

            # Extract service calls (awaited calls) from function body
            service_calls = []
            for body_node in ast.walk(node):
                if isinstance(body_node, ast.Await) and isinstance(body_node.value, ast.Call):
                    call = body_node.value
                    if isinstance(call.func, ast.Name):
                        service_calls.append(call.func.id)
                    elif isinstance(call.func, ast.Attribute):
                        service_calls.append(call.func.attr)

            auth_required = any("current_user" in d or "permission" in d for d in deps)

            routes.append({
                "method": method,
                "path": full_path,
                "handler": node.name,
                "file": _rel(filepath, project_root),
                "line": node.lineno,
                "service_calls": service_calls,
                "auth_required": auth_required,
                "dependencies": deps,
            })

    return routes


def parse_model_file(filepath: Path, project_root: Path) -> list[dict]:
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    models = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        is_table_model = False
        for kw in node.keywords:
            if kw.arg == "table" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                is_table_model = True

        if not is_table_model:
            continue

        table_name = ""
        columns = []
        relationships = []

        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant):
                            table_name = item.value.value
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                col_name = item.target.id
                col_type = ""
                if isinstance(item.annotation, ast.Name):
                    col_type = item.annotation.id
                elif isinstance(item.annotation, ast.Subscript):
                    if isinstance(item.annotation.value, ast.Name):
                        col_type = item.annotation.value.id
                elif isinstance(item.annotation, ast.BinOp):
                    col_type = "Optional"
                elif isinstance(item.annotation, ast.Attribute):
                    col_type = item.annotation.attr

                # Check for foreign_key in Field() — marks a relationship
                is_fk = False
                if item.value and isinstance(item.value, ast.Call):
                    for kw in item.value.keywords:
                        if kw.arg == "foreign_key" and isinstance(kw.value, ast.Constant):
                            fk_table = kw.value.value.split(".")[0]
                            if fk_table not in relationships:
                                relationships.append(fk_table)
                            is_fk = True

                columns.append({"name": col_name, "type": col_type, "is_fk": is_fk})

        models.append({
            "name": node.name,
            "table": table_name,
            "file": _rel(filepath, project_root),
            "line": node.lineno,
            "columns": columns,
            "relationships": relationships,
        })

    return models


def parse_schema_file(filepath: Path, project_root: Path) -> list[dict]:
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    schemas = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        is_basemodel = any(
            (isinstance(base, ast.Name) and base.id == "BaseModel")
            or (isinstance(base, ast.Attribute) and base.attr == "BaseModel")
            for base in node.bases
        )
        if not is_basemodel:
            continue

        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                field_type = ast.dump(item.annotation) if item.annotation else "Any"
                # Simplify type representation
                if isinstance(item.annotation, ast.Name):
                    field_type = item.annotation.id
                elif isinstance(item.annotation, ast.Subscript):
                    if isinstance(item.annotation.value, ast.Name):
                        field_type = f"{item.annotation.value.id}[...]"
                elif isinstance(item.annotation, ast.BinOp):
                    field_type = "Optional"
                elif isinstance(item.annotation, ast.Attribute):
                    field_type = item.annotation.attr

                has_default = item.value is not None
                fields.append({"name": field_name, "type": field_type, "has_default": has_default})

        schemas.append({
            "name": node.name,
            "file": _rel(filepath, project_root),
            "line": node.lineno,
            "fields": fields,
        })

    return schemas


def parse_service_file(filepath: Path, project_root: Path) -> list[dict]:
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    services = []

    module_name = filepath.parent.name

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue

        params = []
        for arg in node.args.args:
            if arg.arg == "self":
                continue
            p_type = ""
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    p_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Attribute):
                    p_type = arg.annotation.attr
                elif isinstance(arg.annotation, ast.Subscript):
                    if isinstance(arg.annotation.value, ast.Name):
                        p_type = f"{arg.annotation.value.id}[...]"
            params.append({"name": arg.arg, "type": p_type})

        # Find model references and function calls in body
        models_used = []
        calls = []
        for body_node in ast.walk(node):
            if isinstance(body_node, ast.Name) and body_node.id[0].isupper():
                if body_node.id not in models_used and body_node.id not in (
                    "HTTPException", "AsyncSession", "None", "True", "False",
                    "Optional", "UUID", "Path", "Query",
                ):
                    models_used.append(body_node.id)
            if isinstance(body_node, ast.Call):
                if isinstance(body_node.func, ast.Attribute) and body_node.func.attr == "delay":
                    if isinstance(body_node.func.value, ast.Name):
                        calls.append(f"{body_node.func.value.id}.delay")

        services.append({
            "name": node.name,
            "module": module_name,
            "file": _rel(filepath, project_root),
            "line": node.lineno,
            "params": params,
            "models_used": models_used,
            "calls": calls,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
        })

    return services


def parse_celery_tasks(filepath: Path, project_root: Path) -> list[dict]:
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    tasks = []

    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not isinstance(deco.func, ast.Attribute):
                continue
            if deco.func.attr != "task":
                continue

            task_name = node.name
            celery_name = ""
            for kw in deco.keywords:
                if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                    celery_name = kw.value.value

            tasks.append({
                "name": celery_name or task_name,
                "function": task_name,
                "file": _rel(filepath, project_root),
                "line": node.lineno,
            })

    return tasks


def parse_backend(backend_dir: Path, project_root: Path) -> dict:
    """Parse all backend files and return a BackendIndex TypedDict."""
    routes: list[dict] = []
    services: list[dict] = []
    models: list[dict] = []
    schemas: list[dict] = []
    tasks: list[dict] = []

    for py_file in backend_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        name = py_file.name

        try:
            if "router" in name and name.endswith(".py"):
                routes.extend(parse_router_file(py_file, project_root))
            elif name == "service.py":
                services.extend(parse_service_file(py_file, project_root))
            elif name == "models.py":
                models.extend(parse_model_file(py_file, project_root))
            elif name == "schemas.py":
                schemas.extend(parse_schema_file(py_file, project_root))
        except SyntaxError:
            continue

    # Parse celery tasks from celery_app.py
    celery_file = project_root / "backend" / "app" / "celery_app.py"
    if celery_file.exists():
        try:
            tasks.extend(parse_celery_tasks(celery_file, project_root))
        except SyntaxError:
            pass

    return {
        "routes": routes,
        "services": services,
        "models": models,
        "schemas": schemas,
        "tasks": tasks,
    }
