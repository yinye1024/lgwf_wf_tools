import json
import pathlib
from typing import Any

import jsonschema


class ToolCatalogError(ValueError):
    def __init__(self, message: str, code: str) -> None:
        self.code = code
        super().__init__(message)


def load_tool_catalog() -> dict[str, Any]:
    path = pathlib.Path(__file__).with_name("catalog.json")
    return json.loads(path.read_text(encoding="utf-8"))


def tool_descriptors() -> dict[str, dict[str, Any]]:
    catalog = load_tool_catalog()
    return {tool["name"]: tool for tool in catalog["tools"]}


def validate_public_tool_options(name: object, options: object) -> dict[str, Any]:
    if not isinstance(name, str) or not name.strip():
        raise ToolCatalogError("tool name must be a non-empty string.", "LGWF_TOOL_UNKNOWN")
    descriptor = tool_descriptors().get(name)
    if descriptor is None or not descriptor.get("public", False):
        raise ToolCatalogError(f"Unknown public tool: {name}", "LGWF_TOOL_UNKNOWN")
    if not isinstance(options, dict):
        raise ToolCatalogError("tool options must be a JSON object.", "LGWF_TOOL_OPTIONS_INVALID")
    try:
        jsonschema.validate(options, descriptor["options_schema"])
    except jsonschema.ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path)
        location = f"options.{path}" if path else "options"
        raise ToolCatalogError(
            f"Invalid options for tool '{name}' at {location}: {exc.message}",
            "LGWF_TOOL_OPTIONS_INVALID",
        ) from exc
    return descriptor
