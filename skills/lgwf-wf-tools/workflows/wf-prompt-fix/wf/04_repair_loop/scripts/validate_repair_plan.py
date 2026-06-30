from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, read_json, write_json


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _allowed_issue_paths(audit: dict[str, Any], selection: dict[str, Any]) -> set[str]:
    selected = {str(item) for item in _as_list(selection.get("selected_issue_ids")) if str(item)}
    if not selected:
        return set()
    allowed: set[str] = set()
    for issue in _as_list(audit.get("issues")):
        if not isinstance(issue, dict) or str(issue.get("id")) not in selected:
            continue
        for key in ("prompt_path", "workflow_path"):
            value = issue.get(key)
            if isinstance(value, str) and value:
                allowed.add(Path(value).as_posix())
    return allowed


def _validate_one(
    raw_path: Any,
    package_root: Path,
    allowed_dirs: list[Path],
    allowed_issue_paths: set[str],
) -> dict[str, Any]:
    raw = str(raw_path)
    path = Path(raw)
    normalized = path.as_posix()
    reasons: list[str] = []
    if not raw:
        reasons.append("empty path")
    if path.is_absolute():
        reasons.append("path must be relative")
    if ".." in path.parts:
        reasons.append("path must not contain '..'")
    if ".lgwf" in path.parts:
        reasons.append("path must not target .lgwf runtime artifacts")

    resolved = (package_root / path).resolve()
    if not _is_under(resolved, package_root):
        reasons.append("path must stay inside target_package_root")
    if allowed_dirs and not any(_is_under(resolved, allowed_dir) for allowed_dir in allowed_dirs):
        reasons.append("path must stay inside target_dirs")
    if allowed_issue_paths and normalized not in allowed_issue_paths:
        reasons.append("path must match a selected issue prompt_path or workflow_path")
    return {
        "path": raw,
        "passed": not reasons,
        "reasons": reasons,
        "resolved_path": str(resolved),
    }


def validate_repair_plan(
    plan: dict[str, Any],
    target: dict[str, Any],
    audit: dict[str, Any] | None = None,
    selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package_root_raw = target.get("target_package_root")
    if not isinstance(package_root_raw, str) or not package_root_raw:
        return {
            "passed": False,
            "artifact_root": ".lgwf/prompt_acceptance",
            "errors": ["target_package_root is required"],
            "file_results": [],
        }
    package_root = Path(package_root_raw).resolve()
    target_dirs = [
        Path(item).resolve()
        for item in _as_list(target.get("target_dirs"))
        if isinstance(item, str) and item
    ] or [package_root]
    audit = audit if isinstance(audit, dict) else {}
    selection = selection if isinstance(selection, dict) else {}
    allowed_issue_paths = _allowed_issue_paths(audit, selection)
    files_to_modify = _as_list(plan.get("files_to_modify"))
    file_results = [_validate_one(item, package_root, target_dirs, allowed_issue_paths) for item in files_to_modify]
    errors = [f"{item['path']}: {', '.join(item['reasons'])}" for item in file_results if not item["passed"]]
    if not isinstance(plan.get("files_to_modify"), list):
        errors.append("repair_plan.files_to_modify must be a list")
    if selection.get("selected_issue_ids") and not allowed_issue_paths:
        errors.append("selected_issue_ids did not resolve to any prompt_path or workflow_path in audit issues")
    return {
        "passed": not errors,
        "artifact_root": ".lgwf/prompt_acceptance",
        "errors": errors,
        "file_results": file_results,
        "allowed_issue_paths": sorted(allowed_issue_paths),
    }


def main() -> None:
    root = lgwf_dir()
    prompt_root = root / "prompt_acceptance"
    plan = read_json(prompt_root / "repair_plan.json", {})
    target = read_json(root / "prompt_fix_target.json", {})
    audit = read_json(prompt_root / "audit.json", {})
    selection = read_json(prompt_root / "fix_selection.json", {})
    if not isinstance(plan, dict):
        plan = {}
    if not isinstance(target, dict):
        target = {}
    if not isinstance(audit, dict):
        audit = {}
    if not isinstance(selection, dict):
        selection = {}
    result = validate_repair_plan(plan, target, audit, selection)
    write_json(prompt_root / "repair_plan_validation.json", result)
    output_state({"repair_plan_validation": result})
    if not result["passed"]:
        raise RuntimeError("repair_plan validation failed: " + "; ".join(result["errors"]))


if __name__ == "__main__":
    main()
