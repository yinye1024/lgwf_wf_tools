from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, read_json, write_json


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _approved_upgrade_ids(decision: dict[str, Any]) -> set[str]:
    return {str(item) for item in _as_list(decision.get("approved_upgrade_ids")) if str(item)}


def _allowed_upgrade_paths(proposal: dict[str, Any], decision: dict[str, Any]) -> set[str]:
    approved = _approved_upgrade_ids(decision)
    allowed: set[str] = set()
    for upgrade in _as_list(proposal.get("prompt_upgrades")):
        if not isinstance(upgrade, dict) or str(upgrade.get("id")) not in approved:
            continue
        for key in ("prompt_path", "workflow_path"):
            value = upgrade.get(key)
            if isinstance(value, str) and value:
                allowed.add(Path(value).as_posix())
        for value in _as_list(upgrade.get("files_to_modify")):
            if isinstance(value, str) and value:
                allowed.add(Path(value).as_posix())
    return allowed


def _validate_path(raw_path: Any, package_root: Path, target_dirs: list[Path], allowed_paths: set[str]) -> dict[str, Any]:
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
    if target_dirs and not any(_is_under(resolved, target_dir) for target_dir in target_dirs):
        reasons.append("path must stay inside target_dirs")
    if allowed_paths and normalized not in allowed_paths:
        reasons.append("path must match an approved upgrade prompt_path, workflow_path, or files_to_modify")
    return {
        "path": raw,
        "passed": not reasons,
        "reasons": reasons,
        "resolved_path": str(resolved),
    }


def validate_apply_plan(
    plan: dict[str, Any],
    target: dict[str, Any],
    proposal: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    package_root_raw = target.get("target_package_root")
    if not isinstance(package_root_raw, str) or not package_root_raw:
        return {
            "passed": False,
            "artifact_root": ".lgwf/prompt_upgrade",
            "errors": ["target_package_root is required"],
            "file_results": [],
            "step_results": [],
        }
    package_root = Path(package_root_raw).resolve()
    target_dirs = [
        Path(item).resolve()
        for item in _as_list(target.get("target_dirs"))
        if isinstance(item, str) and item
    ] or [package_root]
    allowed_paths = _allowed_upgrade_paths(proposal, decision)
    approved = _approved_upgrade_ids(decision)
    files_to_modify = _as_list(plan.get("files_to_modify"))
    file_results = [_validate_path(item, package_root, target_dirs, allowed_paths) for item in files_to_modify]
    step_results: list[dict[str, Any]] = []
    for step in _as_list(plan.get("steps")):
        if not isinstance(step, dict):
            step_results.append({"passed": False, "reasons": ["step must be an object"]})
            continue
        reasons: list[str] = []
        upgrade_id = str(step.get("upgrade_id") or "")
        if upgrade_id not in approved:
            reasons.append("step upgrade_id must be approved")
        file_value = step.get("file")
        if isinstance(file_value, str) and file_value:
            path_result = _validate_path(file_value, package_root, target_dirs, allowed_paths)
            reasons.extend(path_result["reasons"])
        else:
            reasons.append("step file is required")
        step_results.append({"upgrade_id": upgrade_id, "file": file_value, "passed": not reasons, "reasons": reasons})
    errors = [f"{item['path']}: {', '.join(item['reasons'])}" for item in file_results if not item["passed"]]
    errors.extend(
        f"step {item.get('upgrade_id', '')}: {', '.join(item['reasons'])}"
        for item in step_results
        if not item["passed"]
    )
    if not isinstance(plan.get("files_to_modify"), list):
        errors.append("apply_plan.files_to_modify must be a list")
    if decision.get("approved_upgrade_ids") and not allowed_paths:
        errors.append("approved_upgrade_ids did not resolve to any allowed files in proposal")
    return {
        "passed": not errors,
        "artifact_root": ".lgwf/prompt_upgrade",
        "errors": errors,
        "file_results": file_results,
        "step_results": step_results,
        "allowed_paths": sorted(allowed_paths),
    }


def main() -> None:
    root = lgwf_dir()
    upgrade_root = root / "prompt_upgrade"
    plan = read_json(upgrade_root / "apply_plan.json", {})
    target = read_json(root / "prompt_upgrade_target.json", {})
    proposal = read_json(upgrade_root / "proposal.json", {})
    decision = read_json(upgrade_root / "decision.json", {})
    if not isinstance(plan, dict):
        plan = {}
    if not isinstance(target, dict):
        target = {}
    if not isinstance(proposal, dict):
        proposal = {}
    if not isinstance(decision, dict):
        decision = {}
    result = validate_apply_plan(plan, target, proposal, decision)
    write_json(upgrade_root / "apply_plan_validation.json", result)
    output_state({"apply_plan_validation": result})
    if not result["passed"]:
        raise RuntimeError("apply_plan validation failed: " + "; ".join(result["errors"]))


if __name__ == "__main__":
    main()
