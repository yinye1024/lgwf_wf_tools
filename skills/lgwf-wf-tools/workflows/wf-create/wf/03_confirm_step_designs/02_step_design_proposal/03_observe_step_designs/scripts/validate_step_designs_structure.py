"""校验步骤设计 proposal 的结构契约。"""

from __future__ import annotations

import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[4] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from proposal_quality_gate import evaluate_quality_gate, write_json


REQUIRED_STEP_FIELDS = (
    "step_slug",
    "step_name",
    "stage_id",
    "goal",
    "inputs",
    "outputs",
    "dependencies",
    "implementation_suggestions",
    "acceptance_notes",
    "out_of_scope",
    "confirmation_points",
)
LIST_STEP_FIELDS = (
    "inputs",
    "outputs",
    "dependencies",
    "implementation_suggestions",
    "acceptance_notes",
    "out_of_scope",
    "confirmation_points",
)
OPTIONAL_LIST_PATH_FIELDS = ("target_files", "target_dirs", "runtime_artifacts")
FORBIDDEN_DOC_PATH_FIELDS = ("doc_path", "draft_doc_path", "path")
FORBIDDEN_OUT_OF_SCOPE_TERMS = ("lgwf-wf-prompt-fix", "lgwf-wf-tools", "自动修复", "端到端运行保证")


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def check(name: str, passed: bool, message: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "message": message}


def normalize_path_issue(raw_path: Any) -> str:
    if not isinstance(raw_path, str):
        return "路径必须是字符串"
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned:
        return "路径不能为空"
    if candidate.is_absolute():
        return "禁止绝对路径"
    if ":" in cleaned:
        return "禁止盘符路径"
    if any(part == ".." for part in candidate.parts):
        return "禁止 `..`"
    if candidate.parts and candidate.parts[0] == ".lgwf":
        return "禁止指向 `.lgwf` 运行状态目录"
    return ""


def append_path_list_checks(checks: list[dict[str, Any]], index: int, field: str, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        checks.append(check(f"step_designs[{index}]_{field}_list", False, f"step_designs[{index}].{field} 必须是数组"))
        return
    checks.append(check(f"step_designs[{index}]_{field}_list", True, f"step_designs[{index}].{field} 是数组"))
    for item_index, item in enumerate(value):
        issue = normalize_path_issue(item)
        checks.append(
            check(
                f"step_designs[{index}]_{field}[{item_index}]_relative_safe",
                not issue,
                f"step_designs[{index}].{field}[{item_index}] {issue or '是安全相对路径'}",
            )
        )


def append_step_design_contract_checks(result: dict[str, Any], lgwf_dir: Path) -> dict[str, Any]:
    proposal = load_json_object(lgwf_dir / "step_designs_proposal.json")
    business_flow = load_json_object(lgwf_dir / "business_flow.json")
    scaffold = load_json_object(lgwf_dir / "scaffold_package_result.json")
    confirmed_business_flow = nested_dict(business_flow, "confirmed") or business_flow
    scaffold_plan = nested_dict(scaffold, "scaffold_plan") or scaffold
    expected_stage_ids = {
        str(item.get("stage_id", "")).strip()
        for item in [
            *dict_list(confirmed_business_flow.get("stages", [])),
            *dict_list(scaffold_plan.get("stage_manifest", [])),
        ]
        if str(item.get("stage_id", "")).strip()
    }
    checks = result.setdefault("checks", [])
    items = proposal.get("step_designs", [])
    if not isinstance(items, list) or not items:
        checks.append(check("step_designs_present", False, "proposal.step_designs 必须是非空数组"))
        result["passed"] = False
        return result
    checks.append(check("step_designs_present", True, "proposal.step_designs 是非空数组"))

    slugs: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            checks.append(check(f"step_designs[{index}]_object", False, f"step_designs[{index}] 必须是 object"))
            continue
        checks.append(check(f"step_designs[{index}]_object", True, f"step_designs[{index}] 是 object"))
        slug = str(item.get("step_slug", "")).strip()
        if slug:
            duplicate = slug in slugs
            slugs.add(slug)
            checks.append(
                check(
                    f"step_designs[{index}]_step_slug_unique",
                    not duplicate,
                    f"step_slug `{slug}` {'重复' if duplicate else '唯一'}",
                )
            )
        for field in REQUIRED_STEP_FIELDS:
            value = item.get(field)
            if field in LIST_STEP_FIELDS:
                passed = isinstance(value, list) and bool(value)
                message = f"step_designs[{index}].{field} 必须是非空数组"
            else:
                passed = isinstance(value, str) and bool(value.strip())
                message = f"step_designs[{index}].{field} 必须是非空字符串"
            checks.append(check(f"step_designs[{index}]_{field}_present", passed, message))
        source_refs = item.get("source_refs")
        checks.append(
            check(
                f"step_designs[{index}]_source_refs_present",
                isinstance(source_refs, list) and bool(source_refs),
                f"step_designs[{index}].source_refs 必须是非空数组",
            )
        )
        out_of_scope_text = "\n".join(str(value) for value in item.get("out_of_scope", []) if isinstance(value, str))
        for term in FORBIDDEN_OUT_OF_SCOPE_TERMS:
            checks.append(
                check(
                    f"step_designs[{index}]_out_of_scope_mentions_{term}",
                    term in out_of_scope_text,
                    f"step_designs[{index}].out_of_scope 必须排除 {term}",
                )
            )
        stage_id = str(item.get("stage_id", "")).strip()
        if expected_stage_ids and stage_id:
            checks.append(
                check(
                    f"step_designs[{index}]_stage_id_matches",
                    stage_id in expected_stage_ids,
                    f"stage_id `{stage_id}` 必须匹配已确认业务流或 scaffold stage_manifest",
                )
            )
        for field in OPTIONAL_LIST_PATH_FIELDS:
            append_path_list_checks(checks, index, field, item.get(field))
        for field in FORBIDDEN_DOC_PATH_FIELDS:
            raw_value = item.get(field)
            if not isinstance(raw_value, str) or not raw_value.strip():
                checks.append(
                    check(
                        f"step_designs[{index}]_{field}_not_used",
                        True,
                        f"step_designs[{index}] 未使用 {field} 作为步骤设计 Markdown 路径",
                    )
                )
                continue
            checks.append(
                check(
                    f"step_designs[{index}]_{field}_not_used",
                    False,
                    f"step_designs[{index}].{field} 已废弃；步骤设计必须完整内联在 JSON 字段中: {raw_value}",
                )
            )
    result["passed"] = all(item.get("passed") is True for item in checks)
    return result


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    result = evaluate_quality_gate(
        lgwf_dir,
        stage="step_designs",
        proposal_path=lgwf_dir / "step_designs_proposal.json",
        input_paths=[
            lgwf_dir / "business_flow.json",
            lgwf_dir / "create_requirements.json",
            lgwf_dir / "scaffold_package_result.json",
        ],
    )
    result = append_step_design_contract_checks(result, lgwf_dir)
    write_json(lgwf_dir / "step_design_structural_gate.json", result)
    print(
        json.dumps(
            {"lgwf_wf_create.step_design_structural_gate": result},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
