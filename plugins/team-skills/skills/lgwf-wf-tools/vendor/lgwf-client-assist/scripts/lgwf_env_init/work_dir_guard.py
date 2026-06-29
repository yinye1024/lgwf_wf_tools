import json
import pathlib

from .bootstrap import RuntimeSupport


LGWF_ARTIFACT_PATTERNS = (
    ("workflow", "workflow.lgwf"),
    ("workflow", "workflow.json"),
    ("runs", "*.json"),
    ("runs", "*.summary.md"),
    ("runs", "*.feedback.md"),
    ("runs", "*.diff.patch"),
    ("processes", "*.json"),
    ("processes", "*.log"),
    ("checkpoints", "*/checkpoint.json"),
    ("human", "*.request.json"),
    ("human", "*.response.json"),
    ("human", "*.controller_payload.json"),
    ("main_agent", "sessions/*.json"),
    ("logs", "runtime.log"),
)


def validate_rerun_work_dir(work_dir: pathlib.Path, support: RuntimeSupport) -> str | None:
    work_root = work_dir.expanduser().resolve()
    if not work_root.exists():
        return None
    if not work_root.is_dir():
        return f"work_dir must be a directory: {work_root}"
    if _is_empty_directory(work_root):
        return None

    lgwf_dir = support.workspace_layout.lgwf_dir(work_root)
    if not lgwf_dir.is_dir() or lgwf_dir.is_symlink():
        return f"refusing rerun cleanup because work_dir is not an LGWF work directory: {work_root}"

    if _has_lgwf_artifact(lgwf_dir):
        return None
    if _has_valid_context_manifest(lgwf_dir / "context.json"):
        return None

    return f"refusing rerun cleanup because work_dir is not an LGWF work directory: {work_root}"


def _is_empty_directory(path: pathlib.Path) -> bool:
    try:
        next(path.iterdir())
    except StopIteration:
        return True
    return False


def _has_lgwf_artifact(lgwf_dir: pathlib.Path) -> bool:
    for relative_dir, pattern in LGWF_ARTIFACT_PATTERNS:
        marker_dir = lgwf_dir / relative_dir
        if not marker_dir.is_dir() or marker_dir.is_symlink():
            continue
        for candidate in marker_dir.glob(pattern):
            if candidate.is_file() and not candidate.is_symlink():
                return True
    return False


def _has_valid_context_manifest(path: pathlib.Path) -> bool:
    if not path.is_file() or path.is_symlink():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict)
