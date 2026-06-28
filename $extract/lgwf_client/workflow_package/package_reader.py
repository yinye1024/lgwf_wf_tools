import json
from pathlib import Path
from typing import Any

import lgwf_client.workflow_package.types as package_types


WORKFLOW_SOURCE_FILENAME = "workflow.lgwf"
WORKFLOW_FILENAME = "workflow.json"


class WorkflowPackageReadError(ValueError):
    """Raised when a client-side workflow package cannot be read."""


def read_workflow_package(package_root: Path) -> package_types.WorkflowPackagePayload:
    root = package_root.resolve()
    if not root.is_dir():
        raise WorkflowPackageReadError(f"Workflow package root must be a directory: {package_root}")

    entry_path = _select_workflow_source(root)
    if entry_path is None:
        raise WorkflowPackageReadError(
            f"Workflow package must contain root {WORKFLOW_SOURCE_FILENAME} or {WORKFLOW_FILENAME}: {root}"
        )
    entry_relative_path = entry_path.relative_to(root).as_posix()

    workflows: dict[str, package_types.WorkflowDsl] = {}
    for workflow_path in _iter_workflow_sources(root):
        relative_path = workflow_path.relative_to(root).as_posix()
        workflows[relative_path] = _load_workflow_dsl(workflow_path, root)

    return {
        "version": 1,
        "source": "client_package",
        "package_root": str(root),
        "entry_workflow": entry_relative_path,
        "workflow": workflows[entry_relative_path],
        "workflows": workflows,
    }


def _iter_workflow_sources(root: Path) -> list[Path]:
    directories = set()
    for workflow_path in root.rglob(WORKFLOW_SOURCE_FILENAME):
        directories.add(workflow_path.parent)
    for workflow_path in root.rglob(WORKFLOW_FILENAME):
        directories.add(workflow_path.parent)

    workflow_sources: list[Path] = []
    for directory in sorted(directories, key=lambda path: path.relative_to(root).as_posix()):
        workflow_source = _select_workflow_source(directory)
        if workflow_source is not None:
            workflow_sources.append(workflow_source)
    return workflow_sources


def _select_workflow_source(directory: Path) -> Path | None:
    workflow_lgwf = directory / WORKFLOW_SOURCE_FILENAME
    if workflow_lgwf.is_file():
        return workflow_lgwf

    workflow_json = directory / WORKFLOW_FILENAME
    if workflow_json.is_file():
        return workflow_json

    return None


def _load_workflow_dsl(path: Path, package_root: Path) -> package_types.WorkflowDsl:
    if path.name == WORKFLOW_SOURCE_FILENAME:
        return _compile_workflow_source(path, package_root)
    if path.name != WORKFLOW_FILENAME:
        raise WorkflowPackageReadError(f"Unsupported workflow source file: {path}")

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowPackageReadError(f"Failed to read workflow DSL file: {path}") from exc

    try:
        data: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise WorkflowPackageReadError(f"Workflow DSL file is not valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise WorkflowPackageReadError(f"Workflow DSL root must be a JSON object: {path}")

    return data


def _compile_workflow_source(path: Path, package_root: Path) -> package_types.WorkflowDsl:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowPackageReadError(f"Failed to read workflow source file: {path}") from exc

    try:
        import lgwf_dsl.compiler as dsl_compiler_module

        return dsl_compiler_module.WorkflowDslCompiler().compile_text(
            content,
            source_name=str(path),
            package_root=package_root,
        )
    except Exception as exc:
        raise WorkflowPackageReadError(f"Failed to compile workflow source file {path}: {exc}") from exc

