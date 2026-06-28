import json
from pathlib import Path
from typing import Any

import lgwf.workflows.loader as loader_module


WorkflowRegistry = dict[str, Any]
WorkflowEntry = dict[str, Any]

REGISTRY_PATH = Path(__file__).with_name("registry.json")


class WorkflowRegistryError(ValueError):
    """Raised when the workflow registry is invalid."""


def load_registry(path: Path = REGISTRY_PATH) -> WorkflowRegistry:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise WorkflowRegistryError(f"Workflow registry file not found: {path}") from exc
    except OSError as exc:
        raise WorkflowRegistryError(f"Failed to read workflow registry file: {path}") from exc

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise WorkflowRegistryError(f"Workflow registry file is not valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise WorkflowRegistryError(f"Workflow registry root must be a JSON object: {path}")

    validate_registry(data)
    return data


def validate_registry(registry: WorkflowRegistry) -> None:
    version = registry.get("version")
    if version != 1:
        raise WorkflowRegistryError("Workflow registry version must be 1.")

    workflows = registry.get("workflows")
    if not isinstance(workflows, list) or not workflows:
        raise WorkflowRegistryError("Workflow registry must include a non-empty workflows list.")

    keys: set[tuple[str, str]] = set()
    default_count = 0
    for entry in workflows:
        _validate_entry(entry)
        key = (entry["name"], entry["version"])
        if key in keys:
            raise WorkflowRegistryError(f"Duplicate workflow registry entry: {entry['name']}@{entry['version']}")
        keys.add(key)
        if entry.get("default") is True:
            default_count += 1

    if default_count != 1:
        raise WorkflowRegistryError("Workflow registry must include exactly one default workflow.")


def list_workflows(registry: WorkflowRegistry | None = None) -> list[WorkflowEntry]:
    data = registry or load_registry()
    return list(data["workflows"])


def resolve_workflow(
    name: str | None = None,
    version: str | None = None,
    registry_path: Path = REGISTRY_PATH,
) -> WorkflowEntry:
    registry = load_registry(registry_path)
    workflows = registry["workflows"]

    if name is None:
        return _default_workflow(workflows)

    candidates = [
        entry
        for entry in workflows
        if entry["name"] == name and (version is None or entry["version"] == version)
    ]

    if not candidates:
        if version is None:
            raise WorkflowRegistryError(f"Unknown workflow: {name}")
        raise WorkflowRegistryError(f"Unknown workflow: {name}@{version}")

    if len(candidates) > 1:
        raise WorkflowRegistryError(f"Workflow version must be specified for: {name}")

    return candidates[0]


def load_workflow_dsl(
    name: str | None = None,
    version: str | None = None,
    registry_path: Path = REGISTRY_PATH,
) -> loader_module.Dsl:
    entry = resolve_workflow(name=name, version=version, registry_path=registry_path)
    workflow_path = _workflow_path(entry, registry_path)
    return loader_module.load_dsl(workflow_path)


def _validate_entry(entry: Any) -> None:
    if not isinstance(entry, dict):
        raise WorkflowRegistryError("Workflow registry entries must be objects.")

    for field in ("name", "version", "path", "description"):
        value = entry.get(field)
        if not isinstance(value, str) or not value:
            raise WorkflowRegistryError(f"Workflow registry entry field '{field}' must be a non-empty string.")

    default = entry.get("default", False)
    if not isinstance(default, bool):
        raise WorkflowRegistryError("Workflow registry entry field 'default' must be a boolean when provided.")


def _default_workflow(workflows: list[WorkflowEntry]) -> WorkflowEntry:
    for entry in workflows:
        if entry.get("default") is True:
            return entry
    raise WorkflowRegistryError("Workflow registry does not contain a default workflow.")


def _workflow_path(entry: WorkflowEntry, registry_path: Path) -> Path:
    path = Path(entry["path"])
    if path.is_absolute():
        return path
    return registry_path.parent / path

