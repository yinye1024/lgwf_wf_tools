from __future__ import annotations

from pathlib import PurePosixPath
from typing import Iterable


def _normalize_ref(raw: str, *, field: str) -> PurePosixPath:
    cleaned = raw.strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned:
        raise ValueError(f"{field} cannot be empty")
    if path.is_absolute() or ":" in cleaned or any(part == ".." for part in path.parts):
        raise ValueError(f"{field} must use package-relative paths: {raw}")
    return path


def validate_scaffold_paths(paths: Iterable[str]) -> list[str]:
    errors: list[str] = []
    for raw in paths:
        try:
            path = _normalize_ref(raw, field="scaffold path")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if path.name == "workflow.lgwf" and len(path.parts) > 3 and path.parts[0] == "wf":
            errors.append(f"scaffold plan must not create nested workflow: {raw}")
        if path.parts[:2] == ("wf", "tests"):
            errors.append(f"scaffold plan must not create wf/tests: {raw}")
        if len(path.parts) >= 3 and path.parts[:2] == ("wf", "shared") and path.suffix.lower() in {".md", ".lgwf"}:
            errors.append(f"scaffold plan must not put prompt or workflow files under wf/shared: {raw}")
    return errors
