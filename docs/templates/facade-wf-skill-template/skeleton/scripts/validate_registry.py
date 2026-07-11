from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


FACADE_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = FACADE_ROOT / "registry.json"
IGNORED_SKILL_SCAN_PARTS = {".git", ".hg", ".local", ".lgwf", "__pycache__"}
ALLOWED_INPUT_MODES = {"empty_then_approval", "input_json_required", "tool_args", "no_input"}
ALLOWED_AUTO_HUMAN_POLICIES = {"allowed", "conditional", "forbidden", "not_applicable"}


def is_safe_relative_path(raw: Any) -> bool:
    if not isinstance(raw, str) or not raw.strip():
        return False
    path = Path(raw)
    return not path.is_absolute() and ".." not in path.parts


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _append_path_check(checks: list[dict[str, Any]], workflow_id: str, key: str, raw_path: Any) -> None:
    path_safe = is_safe_relative_path(raw_path)
    checks.append({"label": f"{workflow_id}.{key}.relative_path", "passed": path_safe, "path": raw_path})
    if not path_safe:
        return
    full_path = FACADE_ROOT / str(raw_path)
    if key == "work_dir":
        checks.append(
            {
                "label": f"{workflow_id}.{key}.parent_exists",
                "passed": full_path.parent.exists(),
                "path": str(full_path),
            }
        )
    else:
        checks.append({"label": f"{workflow_id}.{key}.exists", "passed": full_path.exists(), "path": str(full_path)})


def check_entry_contract(item: dict[str, Any], workflow_id: str, kind: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    raw_path = item.get("entry_contract")
    path_safe = is_safe_relative_path(raw_path)
    checks.append({"label": f"{workflow_id}.entry_contract.relative_path", "passed": path_safe, "path": raw_path})
    if not path_safe:
        return checks

    contract_path = FACADE_ROOT / str(raw_path)
    checks.append({"label": f"{workflow_id}.entry_contract.exists", "passed": contract_path.is_file(), "path": str(contract_path)})
    if not contract_path.is_file():
        return checks

    try:
        contract = load_json_file(contract_path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        checks.append({"label": f"{workflow_id}.entry_contract.readable_json", "passed": False, "reason": str(exc)})
        return checks

    checks.append({"label": f"{workflow_id}.entry_contract.object", "passed": isinstance(contract, dict)})
    if not isinstance(contract, dict):
        return checks

    checks.append({"label": f"{workflow_id}.entry_contract.id_matches", "passed": contract.get("id") == workflow_id})
    checks.append({"label": f"{workflow_id}.entry_contract.kind_matches", "passed": contract.get("kind") == kind})
    checks.append({"label": f"{workflow_id}.entry_contract.version", "passed": contract.get("version") == 1})
    checks.append(
        {
            "label": f"{workflow_id}.entry_contract.input_mode",
            "passed": contract.get("input_mode") in ALLOWED_INPUT_MODES,
            "value": contract.get("input_mode"),
        }
    )
    checks.append(
        {
            "label": f"{workflow_id}.entry_contract.auto_human_policy",
            "passed": contract.get("auto_human_policy") in ALLOWED_AUTO_HUMAN_POLICIES,
            "value": contract.get("auto_human_policy"),
        }
    )
    input_schema = contract.get("input_schema")
    checks.append(
        {
            "label": f"{workflow_id}.entry_contract.input_schema.object",
            "passed": isinstance(input_schema, dict) and input_schema.get("type") == "object",
        }
    )
    for key in ("input_file_policy", "target_scope", "state_boundary", "outputs", "resume_policy"):
        value = contract.get(key)
        expected_type = str if key in {"input_file_policy", "resume_policy"} else dict
        checks.append({"label": f"{workflow_id}.entry_contract.{key}", "passed": isinstance(value, expected_type)})

    if kind == "lgwf":
        checks.append(
            {
                "label": f"{workflow_id}.entry_contract.workflow_lgwf_matches",
                "passed": contract.get("workflow_lgwf") == item.get("workflow_lgwf"),
            }
        )
        checks.append(
            {
                "label": f"{workflow_id}.entry_contract.work_dir_matches",
                "passed": contract.get("work_dir") == item.get("work_dir"),
            }
        )
    else:
        checks.append(
            {
                "label": f"{workflow_id}.entry_contract.entry_matches",
                "passed": contract.get("entry") == item.get("entry"),
            }
        )
    return checks


def check_workflow_item(item: Any, seen_ids: set[str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not isinstance(item, dict):
        return [{"label": "workflow_item_object", "passed": False, "reason": "workflow item must be object"}]

    workflow_id = item.get("id")
    id_valid = isinstance(workflow_id, str) and bool(workflow_id.strip())
    checks.append({"label": "workflow_id_present", "passed": id_valid, "workflow_id": workflow_id})
    if id_valid:
        checks.append({"label": "workflow_id_unique", "passed": workflow_id not in seen_ids, "workflow_id": workflow_id})
        seen_ids.add(workflow_id)

    kind = item.get("kind", "lgwf")
    kind_valid = kind in {"lgwf", "tool-workflow"}
    checks.append({"label": f"{workflow_id}.kind_supported", "passed": kind_valid, "kind": kind})
    if not id_valid or not kind_valid:
        return checks

    required_paths = ("workflow_lgwf", "work_dir", "agents_md") if kind == "lgwf" else ("entry", "agents_md")
    forbidden_paths = ("workflow_lgwf", "work_dir") if kind == "tool-workflow" else ()
    for key in forbidden_paths:
        checks.append({"label": f"{workflow_id}.{key}.absent", "passed": key not in item, "path": item.get(key)})
    for key in required_paths:
        _append_path_check(checks, workflow_id, key, item.get(key))

    if kind == "lgwf" and is_safe_relative_path(item.get("workflow_lgwf")) and is_safe_relative_path(item.get("work_dir")):
        workflow_root = (FACADE_ROOT / str(item["workflow_lgwf"])).parent
        work_dir = FACADE_ROOT / str(item["work_dir"])
        checks.append(
            {
                "label": f"{workflow_id}.work_dir_not_source_root",
                "passed": workflow_root.resolve() != work_dir.resolve(),
                "workflow_root": str(workflow_root),
                "work_dir": str(work_dir),
            }
        )

    checks.extend(check_entry_contract(item, workflow_id, kind))
    return checks


def run_validation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append({"label": "registry_json_exists", "passed": REGISTRY_PATH.is_file(), "path": str(REGISTRY_PATH)})
    if not REGISTRY_PATH.is_file():
        return {"passed": False, "registry_path": str(REGISTRY_PATH), "checks": checks}

    data = load_json_file(REGISTRY_PATH)
    workflows = data.get("workflows") if isinstance(data, dict) else None
    checks.append({"label": "workflows_list", "passed": isinstance(workflows, list)})
    seen_ids: set[str] = set()
    if isinstance(workflows, list):
        for item in workflows:
            checks.extend(check_workflow_item(item, seen_ids))

    nested_skill_files = [
        str(path.relative_to(FACADE_ROOT))
        for path in (FACADE_ROOT / "workflows").rglob("SKILL.md")
        if not (set(path.relative_to(FACADE_ROOT).parts) & IGNORED_SKILL_SCAN_PARTS)
    ]
    checks.append({"label": "internal_workflows_no_skill_md", "passed": not nested_skill_files, "matches": nested_skill_files})

    return {"passed": all(bool(check.get("passed")) for check in checks), "registry_path": str(REGISTRY_PATH), "checks": checks}


def main() -> None:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"validate_registry failed: {exc}", file=sys.stderr)
        raise
