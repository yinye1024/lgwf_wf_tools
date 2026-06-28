import json
import os
import pathlib
import tempfile
from typing import Any


DEFAULT_ENCODING = "utf-8"


class FileOperationError(ValueError):
    """Raised when LGWF control file IO fails or content is invalid."""


def ensure_dir(path: str | pathlib.Path) -> pathlib.Path:
    directory = pathlib.Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def read_text(path: str | pathlib.Path, *, errors: str = "strict") -> str:
    return pathlib.Path(path).read_text(encoding=DEFAULT_ENCODING, errors=errors)


def write_text_atomic(path: str | pathlib.Path, content: str) -> pathlib.Path:
    target = pathlib.Path(path)
    ensure_dir(target.parent)
    temp_path = _temp_path_for(target)
    try:
        temp_path.write_text(content, encoding=DEFAULT_ENCODING)
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)
    return target


def read_json(path: str | pathlib.Path) -> Any:
    target = pathlib.Path(path)
    try:
        return json.loads(read_text(target))
    except json.JSONDecodeError as exc:
        raise FileOperationError(f"file is not valid JSON: {target}") from exc


def read_json_object(path: str | pathlib.Path, *, label: str = "JSON file") -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict):
        raise FileOperationError(f"{label} must be a JSON object: {path}")
    return data


def write_json_atomic(
    path: str | pathlib.Path,
    data: Any,
    *,
    indent: int | None = 2,
    sort_keys: bool = True,
) -> pathlib.Path:
    text = json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=sort_keys)
    if indent is not None:
        text += "\n"
    return write_text_atomic(path, text)


def resolve_under_root(
    root: str | pathlib.Path,
    relative_path: str | pathlib.Path,
    *,
    allow_missing: bool = True,
) -> pathlib.Path:
    base = pathlib.Path(root).resolve()
    relative = pathlib.Path(relative_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise FileOperationError(f"path must be relative and must not contain '..': {relative_path}")
    resolved = (base / relative).resolve()
    if not _is_relative_to(resolved, base):
        raise FileOperationError(f"path escapes root: {relative_path}")
    if not allow_missing and not resolved.exists():
        raise FileOperationError(f"path does not exist: {resolved}")
    return resolved


def _temp_path_for(target: pathlib.Path) -> pathlib.Path:
    handle = tempfile.NamedTemporaryFile(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
        delete=False,
    )
    handle.close()
    return pathlib.Path(handle.name)


def _is_relative_to(path: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
