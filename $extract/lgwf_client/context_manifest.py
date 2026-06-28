import datetime
import hashlib
from pathlib import Path

import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module
import lgwf_client.types as client_types


DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".lgwf",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


class ContextManifestError(ValueError):
    """Raised when a workspace context manifest cannot be built or loaded."""


def manifest_path(workspace_root: Path) -> Path:
    return workspace_layout_module.context_manifest_path(workspace_root)


def build_manifest(
    workspace_root: Path,
    max_files: int = 500,
    exclude_dirs: set[str] | None = None,
) -> client_types.WorkspaceContext:
    root = workspace_root.resolve()
    if not root.is_dir():
        raise ContextManifestError(f"Workspace root does not exist or is not a directory: {root}")
    if max_files < 1:
        raise ContextManifestError("max_files must be a positive integer.")

    excluded = DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs
    files = _scan_files(root, max_files, excluded)

    return {
        "version": 1,
        "workspace_root": str(root),
        "generated_at": _utc_now(),
        "files": files,
        "stats": {
            "file_count": len(files),
            "max_files": max_files,
            "truncated": len(files) >= max_files,
        },
    }


def save_manifest(
    workspace_root: Path,
    manifest: client_types.WorkspaceContext,
) -> Path:
    path = manifest_path(workspace_root.resolve())
    file_ops_module.write_json_atomic(path, manifest)
    return path


def load_manifest(workspace_root: Path) -> client_types.WorkspaceContext:
    path = manifest_path(workspace_root.resolve())
    try:
        data = file_ops_module.read_json(path)
    except FileNotFoundError as exc:
        raise ContextManifestError(f"Workspace context manifest not found: {path}") from exc
    except OSError as exc:
        raise ContextManifestError(f"Failed to read workspace context manifest: {path}") from exc
    except file_ops_module.FileOperationError as exc:
        raise ContextManifestError(f"Workspace context manifest is not valid JSON: {path}") from exc

    _validate_manifest(data)
    return data


def refresh_manifest(
    workspace_root: Path,
    max_files: int = 500,
    exclude_dirs: set[str] | None = None,
) -> client_types.WorkspaceContext:
    manifest = build_manifest(workspace_root, max_files=max_files, exclude_dirs=exclude_dirs)
    save_manifest(workspace_root, manifest)
    return manifest


def _scan_files(
    root: Path,
    max_files: int,
    exclude_dirs: set[str],
) -> list[client_types.WorkspaceFile]:
    result: list[client_types.WorkspaceFile] = []
    for path in sorted(root.rglob("*")):
        if len(result) >= max_files:
            break
        if not path.is_file():
            continue
        if _is_excluded(path, root, exclude_dirs):
            continue

        relative_path = path.relative_to(root).as_posix()
        result.append(
            {
                "path": relative_path,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return result


def _is_excluded(path: Path, root: Path, exclude_dirs: set[str]) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in exclude_dirs for part in relative_parts[:-1])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _validate_manifest(data: object) -> None:
    if not isinstance(data, dict):
        raise ContextManifestError("Workspace context manifest root must be an object.")

    version = data.get("version")
    if version != 1:
        raise ContextManifestError("Workspace context manifest version must be 1.")

    workspace_root = data.get("workspace_root")
    if not isinstance(workspace_root, str) or not workspace_root:
        raise ContextManifestError("Workspace context manifest workspace_root must be a non-empty string.")

    generated_at = data.get("generated_at")
    if not isinstance(generated_at, str) or not generated_at:
        raise ContextManifestError("Workspace context manifest generated_at must be a non-empty string.")

    files = data.get("files")
    if not isinstance(files, list):
        raise ContextManifestError("Workspace context manifest files must be a list.")
    for item in files:
        _validate_file_entry(item)

    stats = data.get("stats")
    if not isinstance(stats, dict):
        raise ContextManifestError("Workspace context manifest stats must be an object.")


def _validate_file_entry(item: object) -> None:
    if not isinstance(item, dict):
        raise ContextManifestError("Workspace context manifest file entries must be objects.")

    path = item.get("path")
    if not isinstance(path, str) or not path:
        raise ContextManifestError("Workspace context manifest file path must be a non-empty string.")

    size_bytes = item.get("size_bytes")
    if not isinstance(size_bytes, int) or size_bytes < 0:
        raise ContextManifestError("Workspace context manifest file size_bytes must be a non-negative integer.")

    sha256 = item.get("sha256")
    if not isinstance(sha256, str) or len(sha256) != 64:
        raise ContextManifestError("Workspace context manifest file sha256 must be a hex digest string.")


