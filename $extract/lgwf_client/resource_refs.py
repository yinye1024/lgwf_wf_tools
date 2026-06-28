from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ResourceReferenceError(ValueError):
    """Raised when a client-side resource reference is invalid."""


@dataclass(frozen=True)
class ResourceRoots:
    workflow_root: Path | str | None = None
    workspace_root: Path | str | None = None


def resolve_cwd(
    cwd: str | None,
    roots: ResourceRoots | None = None,
) -> Path:
    effective_roots = roots or ResourceRoots()
    if cwd is None:
        return _root_path("workspace", effective_roots, "cwd default workspace root")

    root = Path(cwd).resolve()
    if not root.is_dir():
        raise ResourceReferenceError(f"cwd does not exist or is not a directory: {root}")
    return root


def resolve_resource_path(
    cwd: str,
    reference: dict[str, Any],
    label: str,
    roots: ResourceRoots | None = None,
    ref_root: dict[str, Any] | None = None,
) -> Path:
    if not isinstance(reference, dict):
        raise ResourceReferenceError(f"{label} must be an object.")

    raw_path = reference.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ResourceReferenceError(f"{label}.path must be a non-empty string.")

    root_name = reference.get("root")
    if root_name is not None:
        return _resolve_rooted_reference(reference, label, roots or ResourceRoots())

    if ref_root is not None:
        if not isinstance(ref_root, dict):
            raise ResourceReferenceError("ref_root must be an object.")
        effective_roots = roots or ResourceRoots()
        root = _resolve_rooted_reference(ref_root, "ref_root", effective_roots)
        path = _relative_path(raw_path, label)
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            raise ResourceReferenceError(f"{label}.path must stay inside ref_root.")
        return resolved

    root = Path(cwd).resolve()
    if not root.is_dir():
        raise ResourceReferenceError(f"cwd does not exist or is not a directory: {root}")

    path = _relative_path(raw_path, label)
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ResourceReferenceError(f"{label}.path must stay inside cwd.")

    return resolved


def read_text_resource(
    cwd: str,
    reference: dict[str, Any],
    label: str,
    roots: ResourceRoots | None = None,
    ref_root: dict[str, Any] | None = None,
) -> str:
    path = resolve_resource_path(cwd, reference, label, roots, ref_root)
    if not path.is_file():
        raise ResourceReferenceError(f"{label}.path does not exist or is not a file: {path}")
    return path.read_text(encoding="utf-8")


def _resolve_rooted_reference(
    reference: dict[str, Any],
    label: str,
    roots: ResourceRoots,
) -> Path:
    raw_root = reference.get("root")
    if raw_root not in {"workflow", "workspace"}:
        raise ResourceReferenceError(f"{label}.root must be one of: workflow, workspace.")

    raw_path = reference.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ResourceReferenceError(f"{label}.path must be a non-empty string.")

    root = _root_path(raw_root, roots, label)
    path = _relative_path(raw_path, label)
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ResourceReferenceError(f"{label}.path must stay inside {raw_root} root.")
    return resolved


def _root_path(root_name: str, roots: ResourceRoots, label: str) -> Path:
    raw_root = roots.workflow_root if root_name == "workflow" else roots.workspace_root
    if raw_root is None:
        raise ResourceReferenceError(f"{label}.root '{root_name}' is not configured.")

    root = Path(raw_root).resolve()
    if not root.is_dir():
        raise ResourceReferenceError(f"{label}.root '{root_name}' does not exist or is not a directory: {root}")
    return root


def _relative_path(raw_path: str, label: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        raise ResourceReferenceError(f"{label}.path must be relative.")
    if ".." in path.parts:
        raise ResourceReferenceError(f"{label}.path must not contain '..'.")
    return path

