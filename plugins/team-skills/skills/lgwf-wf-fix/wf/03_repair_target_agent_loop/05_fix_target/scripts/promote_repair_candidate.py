from __future__ import annotations

import shutil
import sys
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state
from target_repair_loop import archive_current_iteration, load_current_artifact, write_current_artifact


def _normalize_relative_path(raw: Any) -> str:
    relative = str(raw).replace("\\", "/").strip("/")
    if not relative.strip():
        return ""
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} or ":" in part for part in path.parts):
        raise ValueError(f"change_audit.changed_files contains unsafe relative path: {raw}")
    return path.as_posix()


def _relative_paths(change_audit: dict[str, Any]) -> list[str]:
    raw = change_audit.get("changed_files")
    if not isinstance(raw, list):
        return []
    return sorted({relative for path in raw if (relative := _normalize_relative_path(path))})


def promote_candidate_changes(candidate_root: Path, target_root: Path, change_audit: dict[str, Any]) -> dict[str, Any]:
    if change_audit.get("passed") is not True:
        raise ValueError("change_audit.passed must be true before promote")
    if change_audit.get("unexpected_changes"):
        raise ValueError("change_audit.unexpected_changes must be empty before promote")

    candidate_root = candidate_root.resolve()
    target_root = target_root.resolve()
    promoted: list[str] = []
    for relative in _relative_paths(change_audit):
        source = candidate_root / relative
        target = target_root / relative
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        elif target.exists():
            target.unlink()
        promoted.append(relative)
    return {
        "status": "promoted",
        "candidate_package_root": str(candidate_root),
        "target_package_root": str(target_root),
        "target_dirs": [str(target_root)],
        "promoted_files": promoted,
    }


def main() -> None:
    root = lgwf_dir()
    target = load_self_fix_target()
    workspace = load_current_artifact(root, "workspace", {})
    change_audit = load_current_artifact(root, "change_audit", {})
    if not isinstance(workspace, dict):
        workspace = {}
    if not isinstance(change_audit, dict):
        change_audit = {}
    candidate_root = Path(str(workspace.get("candidate_package_root") or ""))
    target_root = Path(str(target.get("target_package_root") or workspace.get("source_package_root") or ""))
    if not candidate_root.exists():
        raise ValueError(f"candidate_package_root must exist before promote: {candidate_root}")
    if not target_root.exists():
        raise ValueError(f"target_package_root must exist before promote: {target_root}")

    result = promote_candidate_changes(candidate_root, target_root, change_audit)
    write_current_artifact(root, "promote", result)
    archive_current_iteration(root, outcome="promote")
    append_history({"event": "repair_candidate_promoted", "promoted_files": result["promoted_files"]})
    output_state({"target_repair_promote": result, "target_dirs": result["target_dirs"]})


if __name__ == "__main__":
    main()
