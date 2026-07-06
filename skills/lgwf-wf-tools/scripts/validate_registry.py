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


def _nested_required_fields(schema: Any) -> list[str]:
    if not isinstance(schema, dict):
        return []
    required = schema.get("required")
    return [item for item in required if isinstance(item, str)] if isinstance(required, list) else []


def check_entry_contract(item: dict[str, Any], workflow_id: str, kind: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    raw_path = item.get("entry_contract")
    path_safe = is_safe_relative_path(raw_path)
    checks.append({"label": f"{workflow_id}.entry_contract.relative_path", "passed": path_safe, "path": raw_path})
    if not path_safe:
        return checks

    contract_path = FACADE_ROOT / str(raw_path)
    contract_exists = contract_path.is_file()
    checks.append({"label": f"{workflow_id}.entry_contract.exists", "passed": contract_exists, "path": str(contract_path)})
    if not contract_exists:
        return checks

    try:
        contract = load_json_file(contract_path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        checks.append(
            {
                "label": f"{workflow_id}.entry_contract.readable_json",
                "passed": False,
                "path": str(contract_path),
                "reason": str(exc),
            }
        )
        return checks

    contract_is_object = isinstance(contract, dict)
    checks.append({"label": f"{workflow_id}.entry_contract.object", "passed": contract_is_object})
    if not contract_is_object:
        return checks

    checks.append({"label": f"{workflow_id}.entry_contract.id_matches", "passed": contract.get("id") == workflow_id})
    checks.append({"label": f"{workflow_id}.entry_contract.kind_matches", "passed": contract.get("kind") == kind})
    checks.append({"label": f"{workflow_id}.entry_contract.version", "passed": contract.get("version") == 1})

    input_mode = contract.get("input_mode")
    checks.append(
        {
            "label": f"{workflow_id}.entry_contract.input_mode",
            "passed": input_mode in ALLOWED_INPUT_MODES,
            "value": input_mode,
        }
    )
    auto_policy = contract.get("auto_human_policy")
    checks.append(
        {
            "label": f"{workflow_id}.entry_contract.auto_human_policy",
            "passed": auto_policy in ALLOWED_AUTO_HUMAN_POLICIES,
            "value": auto_policy,
        }
    )

    input_schema = contract.get("input_schema")
    schema_is_object = isinstance(input_schema, dict) and input_schema.get("type") == "object"
    checks.append({"label": f"{workflow_id}.entry_contract.input_schema.object", "passed": schema_is_object})
    if schema_is_object:
        checks.append(
            {
                "label": f"{workflow_id}.entry_contract.input_schema.properties",
                "passed": isinstance(input_schema.get("properties"), dict),
            }
        )
        checks.append(
            {
                "label": f"{workflow_id}.entry_contract.input_schema.required",
                "passed": isinstance(input_schema.get("required"), list),
                "required": _nested_required_fields(input_schema),
            }
        )
        example_required = input_mode not in {"tool_args", "no_input"}
        example = input_schema.get("example")
        checks.append(
            {
                "label": f"{workflow_id}.entry_contract.input_schema.example",
                "passed": isinstance(example, dict) or not example_required,
            }
        )

    for key in ("input_file_policy", "target_scope", "state_boundary", "outputs", "resume_policy"):
        value = contract.get(key)
        expected_type = str if key in {"input_file_policy", "resume_policy"} else dict
        checks.append(
            {
                "label": f"{workflow_id}.entry_contract.{key}",
                "passed": isinstance(value, expected_type),
            }
        )

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
                "label": f"{workflow_id}.entry_contract.entry_present",
                "passed": isinstance(contract.get("entry"), str) and bool(contract.get("entry")),
                "entry": contract.get("entry"),
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
    if not kind_valid:
        return checks

    required_paths = ("workflow_lgwf", "work_dir", "agents_md") if kind == "lgwf" else ("entry", "agents_md")
    forbidden_paths = ("workflow_lgwf", "work_dir") if kind == "tool-workflow" else ()

    for key in forbidden_paths:
        checks.append({"label": f"{workflow_id}.{key}.absent", "passed": key not in item, "path": item.get(key)})

    for key in required_paths:
        raw_path = item.get(key)
        path_safe = is_safe_relative_path(raw_path)
        checks.append({"label": f"{workflow_id}.{key}.relative_path", "passed": path_safe, "path": raw_path})
        if path_safe:
            full_path = FACADE_ROOT / str(raw_path)
            if key == "work_dir":
                checks.append(
                    {
                        "label": f"{workflow_id}.{key}.parent_exists",
                        "passed": full_path.parent.exists(),
                        "path": str(full_path),
                        "parent": str(full_path.parent),
                    }
                )
            else:
                checks.append({"label": f"{workflow_id}.{key}.exists", "passed": full_path.exists(), "path": str(full_path)})

    workflow_lgwf = item.get("workflow_lgwf")
    work_dir = item.get("work_dir")
    if kind == "lgwf" and is_safe_relative_path(workflow_lgwf) and is_safe_relative_path(work_dir):
        workflow_root = (FACADE_ROOT / str(workflow_lgwf)).parent
        work_dir_path = FACADE_ROOT / str(work_dir)
        checks.append(
            {
                "label": f"{workflow_id}.work_dir_not_source_root",
                "passed": workflow_root.resolve() != work_dir_path.resolve(),
                "workflow_root": str(workflow_root),
                "work_dir": str(work_dir_path),
            }
        )

    if id_valid:
        checks.extend(check_entry_contract(item, workflow_id, kind))

    return checks


def run_validation() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    registry_exists = REGISTRY_PATH.is_file()
    checks.append({"label": "registry_json_exists", "passed": registry_exists, "path": str(REGISTRY_PATH)})
    if not registry_exists:
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
    checks.append(
        {
            "label": "internal_workflows_no_skill_md",
            "passed": not nested_skill_files,
            "matches": nested_skill_files,
        }
    )

    return {
        "passed": all(bool(check.get("passed")) for check in checks),
        "registry_path": str(REGISTRY_PATH),
        "checks": checks,
    }


def main() -> None:
    result = run_validation()
    print(json.dumps(result, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"validate_registry failed: {exc}", file=sys.stderr)
        raise
