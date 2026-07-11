from __future__ import annotations

from pathlib import Path


def find_workflow_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "self-improve" / "manifest.json").is_file():
            return candidate
    raise RuntimeError(f"cannot find workflow root from {current}")


def workflow_source() -> Path:
    package_source = WORKFLOW_ROOT / "wf" / "workflow.lgwf"
    root_source = WORKFLOW_ROOT / "workflow.lgwf"
    if package_source.is_file():
        return package_source
    if root_source.is_file():
        return root_source
    raise FileNotFoundError(f"cannot find workflow.lgwf under {WORKFLOW_ROOT}")


WORKFLOW_ROOT = find_workflow_root()
SELF_IMPROVE_ROOT = WORKFLOW_ROOT / "self-improve"
LOCAL_SELF_IMPROVE = WORKFLOW_ROOT / ".local" / "self-improve"
