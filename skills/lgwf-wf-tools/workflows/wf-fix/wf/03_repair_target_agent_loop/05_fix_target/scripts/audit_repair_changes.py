from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state
from target_repair_loop import load_current_artifact, write_current_artifact


EXCLUDED_DIRS = {".git", ".hg", ".svn", ".lgwf", "__pycache__", ".pytest_cache"}


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _current_files(package_root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in package_root.rglob("*"):
        if not path.is_file() or _is_excluded(path.relative_to(package_root)):
            continue
        files[path.relative_to(package_root).as_posix()] = _hash_file(path)
    return files


def _allowed_files(plan: dict[str, Any]) -> set[str]:
    raw = plan.get("files_to_modify")
    if not isinstance(raw, list):
        return set()
    return {str(path).replace("\\", "/").strip("/") for path in raw if str(path).strip()}


def audit_candidate_changes(baseline_root: Path, candidate_root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    before = _current_files(baseline_root)
    current = _current_files(candidate_root)
    changed = sorted(path for path in set(before) | set(current) if before.get(path) != current.get(path))
    allowed = _allowed_files(plan)
    planned = sorted(path for path in changed if path in allowed)
    unexpected = sorted(path for path in changed if path not in allowed)
    missing_planned = sorted(path for path in allowed if path not in changed)
    return {
        "passed": not unexpected,
        "changed_files": changed,
        "planned_changes": planned,
        "unexpected_changes": unexpected,
        "missing_planned_changes": missing_planned,
        "allowed_files": sorted(allowed),
        "baseline_package_root": str(baseline_root),
        "candidate_package_root": str(candidate_root),
    }


def main() -> None:
    root = lgwf_dir()
    plan = load_current_artifact(root, "plan", {})
    workspace = load_current_artifact(root, "workspace", {})
    if not isinstance(plan, dict):
        plan = {}
    if not isinstance(workspace, dict):
        workspace = {}
    if not workspace.get("baseline_package_root") or not workspace.get("candidate_package_root"):
        raise ValueError(".lgwf/target_repair/current/workspace.json must contain baseline_package_root and candidate_package_root")
    audit = audit_candidate_changes(
        Path(str(workspace["baseline_package_root"])),
        Path(str(workspace["candidate_package_root"])),
        plan,
    )
    write_current_artifact(root, "change_audit", audit)
    append_history({"event": "repair_changes_audited", "passed": audit["passed"], "unexpected": audit["unexpected_changes"]})
    output_state({"target_repair_current_change_audit": audit, "repair_change_audit_passed": audit["passed"]})


if __name__ == "__main__":
    main()
