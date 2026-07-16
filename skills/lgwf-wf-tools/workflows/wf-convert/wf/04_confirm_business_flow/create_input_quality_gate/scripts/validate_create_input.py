"""对 wf-create-fast 输入 proposal 执行确定性质量检查。"""

from __future__ import annotations

import json
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from observe_protocol import build_observer_report, make_issue, read_json_object, write_json


STAGE = "proposal"
REQUIRED_TYPES = {
    "workflow_name": str,
    "target_package_root": str,
    "raw_intent": str,
    "source_root": str,
    "stages": list,
    "prompt_contracts": list,
    "source_business_contract": dict,
    "prompt_execution_mechanics": list,
    "presentation_constraints": list,
    "discarded_prompt_techniques": list,
    "conversion_mapping": list,
    "parity_requirements": list,
    "human_approval_points": list,
    "assumptions": list,
    "out_of_scope": list,
    "run_workflow_notes_for_wf_create_fast": list,
}
MAPPING_TYPES = {
    "preserve_business_logic",
    "convert_to_lgwf_node",
    "convert_to_script",
    "convert_to_schema_constraint",
    "discard_prompt_technique",
    "manual_confirmation_required",
}


def issue(
    code: str,
    field: str,
    message: str,
    required_change: str,
    *,
    blocking: bool = True,
    severity: str = "high",
) -> dict[str, Any]:
    return make_issue(
        observer="python",
        code=code,
        field=field,
        blocking=blocking,
        severity=severity,
        issue=message,
        required_change=required_change,
    )


def has_valid_target_package_root(value: Any) -> bool:
    raw = str(value or "").strip()
    if "://" in raw or not raw or raw == ".":
        return False
    if ":" in raw:
        candidate = PureWindowsPath(raw)
        if not candidate.is_absolute():
            return False
        parts = candidate.parts
    else:
        candidate = PurePosixPath(raw.replace("\\", "/"))
        parts = candidate.parts
    return not any(part in {"..", ".lgwf"} for part in parts)


def _business_rule_ids(contract: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for value in contract.values():
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, dict) and str(item.get("rule_id", "")).strip():
                result.add(str(item["rule_id"]).strip())
    return result


def _inspection_stage_ids(inspection: dict[str, Any]) -> set[str]:
    values = inspection.get("detected_stages", [])
    return {
        str(item.get("stage_id", "")).strip()
        for item in values
        if isinstance(item, dict) and str(item.get("stage_id", "")).strip()
    }


def _inspection_prompt_paths(inspection: dict[str, Any]) -> set[str]:
    values = inspection.get("prompt_contracts", [])
    return {
        str(item.get("prompt_path", "")).strip().replace("\\", "/")
        for item in values
        if isinstance(item, dict) and str(item.get("prompt_path", "")).strip()
    }


def validate_create_input(proposal: dict[str, Any], inspection: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for key, expected_type in REQUIRED_TYPES.items():
        if key not in proposal:
            issues.append(issue("MISSING_REQUIRED_FIELD", key, "proposal 缺少必填字段", f"补充顶层字段 {key}"))
        elif not isinstance(proposal[key], expected_type):
            issues.append(issue("INVALID_FIELD_TYPE", key, f"{key} 必须是 {expected_type.__name__}", f"按固定契约重写 {key}"))
    if issues:
        return issues

    for key in ("workflow_name", "raw_intent", "source_root"):
        if not proposal[key].strip():
            issues.append(issue("EMPTY_REQUIRED_VALUE", key, f"{key} 不得为空", f"补充 {key}"))
    if not has_valid_target_package_root(proposal["target_package_root"]):
        issues.append(
            issue(
                "INVALID_TARGET_PACKAGE_ROOT",
                "target_package_root",
                "目标路径为空、为点路径、URL、包含 .. 或 .lgwf，或 Windows 盘符路径不是绝对路径",
                "改为合法绝对路径或安全相对路径",
            )
        )

    inspection_stage_ids = _inspection_stage_ids(inspection)
    for index, item in enumerate(proposal["stages"]):
        field = f"stages[{index}]"
        if not isinstance(item, dict):
            issues.append(issue("INVALID_ITEM_TYPE", field, "stage 必须是对象", "按固定 stage 契约重写"))
            continue
        for key in ("stage_id", "name", "responsibility", "inputs", "outputs", "source_files", "evidence_strength", "evidence_summary"):
            if key not in item:
                issues.append(issue("MISSING_REQUIRED_FIELD", f"{field}.{key}", "stage 缺少必填字段", f"补充 {key}"))
        stage_id = str(item.get("stage_id", "")).strip()
        if stage_id and stage_id not in inspection_stage_ids:
            issues.append(issue("STAGE_NOT_TRACEABLE", f"{field}.stage_id", f"stage_id 未出现在 inspection：{stage_id}", "只保留 inspection 中可追溯的高置信 stage"))
        if item.get("evidence_strength") != "high":
            issues.append(issue("STAGE_NOT_HIGH_CONFIDENCE", f"{field}.evidence_strength", "proposal stages 只允许高置信条目", "降级到 assumptions 或人工确认提示"))

    inspection_prompt_paths = _inspection_prompt_paths(inspection)
    for index, item in enumerate(proposal["prompt_contracts"]):
        field = f"prompt_contracts[{index}]"
        if not isinstance(item, dict):
            issues.append(issue("INVALID_ITEM_TYPE", field, "prompt_contract 必须是对象", "按固定 prompt contract 契约重写"))
            continue
        for key in ("prompt_path", "responsibility", "inputs", "outputs", "constraints", "source_files", "evidence_strength", "evidence_summary"):
            if key not in item:
                issues.append(issue("MISSING_REQUIRED_FIELD", f"{field}.{key}", "prompt contract 缺少必填字段", f"补充 {key}"))
        prompt_path = str(item.get("prompt_path", "")).strip().replace("\\", "/")
        if prompt_path and prompt_path not in inspection_prompt_paths:
            issues.append(issue("PROMPT_CONTRACT_NOT_TRACEABLE", f"{field}.prompt_path", f"prompt_path 未出现在 inspection：{prompt_path}", "只保留 inspection 中可追溯的高置信 prompt contract"))
        if item.get("evidence_strength") != "high":
            issues.append(issue("PROMPT_CONTRACT_NOT_HIGH_CONFIDENCE", f"{field}.evidence_strength", "proposal prompt_contracts 只允许高置信条目", "降级到 assumptions 或人工确认提示"))

    rule_ids = _business_rule_ids(proposal["source_business_contract"])
    mapped_rule_ids: set[str] = set()
    for index, item in enumerate(proposal["conversion_mapping"]):
        field = f"conversion_mapping[{index}]"
        if not isinstance(item, dict):
            issues.append(issue("INVALID_ITEM_TYPE", field, "conversion mapping 必须是对象", "按固定 mapping 契约重写"))
            continue
        for key in ("mapping_id", "source_rule_ids", "mapping_type", "target_design", "rationale"):
            if key not in item:
                issues.append(issue("MISSING_REQUIRED_FIELD", f"{field}.{key}", "mapping 缺少必填字段", f"补充 {key}"))
        if item.get("mapping_type") not in MAPPING_TYPES:
            issues.append(issue("INVALID_MAPPING_TYPE", f"{field}.mapping_type", "mapping_type 枚举非法", "改用允许的 mapping_type"))
        source_rule_ids = item.get("source_rule_ids")
        if not isinstance(source_rule_ids, list) or not source_rule_ids:
            issues.append(issue("MISSING_SOURCE_RULE_IDS", f"{field}.source_rule_ids", "mapping 必须引用至少一个业务规则 ID", "补充 source_rule_ids"))
            continue
        for rule_id in source_rule_ids:
            normalized = str(rule_id).strip()
            if normalized not in rule_ids:
                issues.append(issue("UNKNOWN_SOURCE_RULE_ID", f"{field}.source_rule_ids", f"引用了未知业务规则：{normalized}", "改为 source_business_contract 中存在的 rule_id"))
            else:
                mapped_rule_ids.add(normalized)

    parity_rule_ids: set[str] = set()
    for index, item in enumerate(proposal["parity_requirements"]):
        field = f"parity_requirements[{index}]"
        if not isinstance(item, dict):
            issues.append(issue("INVALID_ITEM_TYPE", field, "parity requirement 必须是对象", "按固定 parity 契约重写"))
            continue
        for key in ("requirement_id", "source_rule_ids", "description", "verification"):
            if key not in item:
                issues.append(issue("MISSING_REQUIRED_FIELD", f"{field}.{key}", "parity requirement 缺少必填字段", f"补充 {key}"))
        source_rule_ids = item.get("source_rule_ids")
        if not isinstance(source_rule_ids, list) or not source_rule_ids:
            issues.append(issue("MISSING_SOURCE_RULE_IDS", f"{field}.source_rule_ids", "parity requirement 必须引用业务规则 ID", "补充 source_rule_ids"))
            continue
        for rule_id in source_rule_ids:
            normalized = str(rule_id).strip()
            if normalized not in rule_ids:
                issues.append(issue("UNKNOWN_SOURCE_RULE_ID", f"{field}.source_rule_ids", f"引用了未知业务规则：{normalized}", "改为 source_business_contract 中存在的 rule_id"))
            else:
                parity_rule_ids.add(normalized)

    for missing_rule_id in sorted(rule_ids - mapped_rule_ids):
        issues.append(issue("UNMAPPED_BUSINESS_RULE", "conversion_mapping", f"业务规则未被 conversion_mapping 覆盖：{missing_rule_id}", "为该规则补充 conversion mapping"))
    for missing_rule_id in sorted(rule_ids - parity_rule_ids):
        issues.append(issue("MISSING_PARITY_COVERAGE", "parity_requirements", f"业务规则未被 parity requirements 覆盖：{missing_rule_id}", "为该规则补充一致性验证要求"))

    if not proposal["out_of_scope"]:
        issues.append(issue("EMPTY_OUT_OF_SCOPE", "out_of_scope", "out_of_scope 不得为空", "声明不直接生成最终 package、不跳过人工确认等边界"))
    return issues


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    try:
        proposal = read_json_object(lgwf_dir / "wf_create_fast_input_proposal.json")
        inspection = read_json_object(lgwf_dir / "prompt_workflow_inspection.json")
        issues = validate_create_input(proposal, inspection)
    except (FileNotFoundError, json.JSONDecodeError, TypeError) as exc:
        issues = [issue("INVALID_PROPOSAL_JSON", "wf_create_fast_input_proposal", f"proposal 或 inspection 无法解析：{exc}", "重新执行对应 Act 并输出合法 JSON")]
    report = build_observer_report(stage=STAGE, observer="python", issues=issues)
    write_json(lgwf_dir / "wf_create_fast_input_observe_py.json", report)
    print(json.dumps({"lgwf_wf_convert.propose_python_observe": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
