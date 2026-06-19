from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state, read_json, write_json


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


def audit_changes(package_root: Path, snapshot: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    before = snapshot.get("files") if isinstance(snapshot.get("files"), dict) else {}
    current = _current_files(package_root)
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
    }


def main() -> None:
    root = lgwf_dir()
    target = load_self_fix_target()
    package_root = Path(str(target.get("target_package_root") or "")).resolve()
    snapshot = read_json(root / "target_repair_snapshot.json", {})
    plan = read_json(root / "target_repair_plan.json", {})
    if not isinstance(snapshot, dict):
        snapshot = {}
    if not isinstance(plan, dict):
        plan = {}
    audit = audit_changes(package_root, snapshot, plan)
    write_json(root / "target_repair_change_audit.json", audit)
    append_history({"event": "repair_changes_audited", "passed": audit["passed"], "unexpected": audit["unexpected_changes"]})
    output_state({"target_repair_change_audit": audit, "repair_change_audit_passed": audit["passed"]})


if __name__ == "__main__":
    main()
