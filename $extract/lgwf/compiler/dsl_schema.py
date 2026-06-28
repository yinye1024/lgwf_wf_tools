import json
from pathlib import Path
from typing import Any


DslSchema = dict[str, Any]

SCHEMA_PATH = Path(__file__).with_name("dsl_schema.json")


class DSLSchemaLoadError(ValueError):
    """Raised when the workflow DSL schema cannot be loaded."""


class DSLSchemaValidationError(ValueError):
    """Raised when the workflow DSL schema document is invalid."""


def load_schema(path: Path = SCHEMA_PATH) -> DslSchema:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DSLSchemaLoadError(f"Workflow DSL schema file not found: {path}") from exc
    except OSError as exc:
        raise DSLSchemaLoadError(f"Failed to read workflow DSL schema file: {path}") from exc

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise DSLSchemaLoadError(f"Workflow DSL schema file is not valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise DSLSchemaLoadError(f"Workflow DSL schema root must be a JSON object: {path}")

    validate_schema(data)
    return data


def validate_schema(schema: DslSchema) -> None:
    version = schema.get("version")
    if not isinstance(version, int) or version < 1:
        raise DSLSchemaValidationError("Workflow DSL schema must include a positive integer version.")

    top_level_fields = schema.get("top_level_fields")
    if not isinstance(top_level_fields, dict):
        raise DSLSchemaValidationError("Workflow DSL schema must include top_level_fields object.")

    for field in ("nodes", "edges", "routes", "entry_point"):
        if field not in top_level_fields:
            raise DSLSchemaValidationError(f"Workflow DSL schema missing top-level field: {field}")

    node_schema = schema.get("node")
    if not isinstance(node_schema, dict):
        raise DSLSchemaValidationError("Workflow DSL schema must include node object.")

    route_schema = schema.get("route")
    if not isinstance(route_schema, dict):
        raise DSLSchemaValidationError("Workflow DSL schema must include route object.")

    edge_schema = schema.get("edge")
    if not isinstance(edge_schema, dict):
        raise DSLSchemaValidationError("Workflow DSL schema must include edge object.")

    constraints = schema.get("constraints")
    if not isinstance(constraints, list) or any(not isinstance(item, str) for item in constraints):
        raise DSLSchemaValidationError("Workflow DSL schema constraints must be a list of strings.")

