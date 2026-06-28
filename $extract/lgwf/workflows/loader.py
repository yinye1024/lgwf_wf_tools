import json
from pathlib import Path
from typing import Any


Dsl = dict[str, Any]


class WorkflowLoadError(ValueError):
    """Raised when a workflow DSL file cannot be loaded."""


def load_dsl(path: Path) -> Dsl:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise WorkflowLoadError(f"Workflow DSL file not found: {path}") from exc
    except OSError as exc:
        raise WorkflowLoadError(f"Failed to read workflow DSL file: {path}") from exc

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise WorkflowLoadError(f"Workflow DSL file is not valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise WorkflowLoadError(f"Workflow DSL root must be a JSON object: {path}")

    return data

