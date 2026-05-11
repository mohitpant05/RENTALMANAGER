def validate_attributes(
    attributes: dict | None,
    schema: list[dict] | None,
) -> list[str]:
    if not schema:
        return []
    attrs = attributes or {}
    errors: list[str] = []

    for field_def in schema:
        name = field_def["name"]
        field_type = field_def["type"]
        required = field_def.get("required", False)
        value = attrs.get(name)

        if value is None:
            if required:
                errors.append(f"Required attribute '{name}' is missing")
            continue

        type_error = _check_type(name, value, field_type, field_def)
        if type_error:
            errors.append(type_error)

    return errors


_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "text": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "tags": lambda v: isinstance(v, list) and all(isinstance(t, str) for t in v),
}


def _check_type(name: str, value, field_type: str, field_def: dict) -> str | None:
    if field_type == "enum":
        options = field_def.get("options", [])
        if value not in options:
            return f"Attribute '{name}' must be one of {options}, got '{value}'"
        return None

    checker = _TYPE_CHECKS.get(field_type)
    if checker and not checker(value):
        return f"Attribute '{name}' must be type '{field_type}', got {type(value).__name__}"
    return None
