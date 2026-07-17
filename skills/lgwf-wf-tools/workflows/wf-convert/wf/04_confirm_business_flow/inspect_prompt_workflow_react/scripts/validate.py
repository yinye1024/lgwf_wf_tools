"""对 prompt workflow inspection 执行确定性质量检查。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from observe_protocol import build_observer_report, make_issue, read_json_object, write_json


STAGE = "inspection"
REQUIRED_TYPES = {
    "source_summary": list,
    "detected_stages": list,
    "prompt_contracts": list,
    "source_business_contract": dict,
    "prompt_execution_mechanics": list,
    "presentation_constraints": list,
    "discarded_prompt_techniques": list,
    "human_approval_points": list,
    "gaps": list,
    "risks": list,
    "assumptions": list,
}
BUSINESS_CONTRACT_FIELDS = (
    "goal",
    "inputs",
    "outputs",
    "stages",
    "decision_rules",
    "approval_points",
    "error_paths",
    "invariants",
)
EVIDENCE_STRENGTHS = {"high", "medium", "low"}
PROPOSAL_CONSUMERS = {
    "raw_intent",
    "stages",
    "prompt_contracts",
    "human_approval_points",
    "approval_reference",
    "assumptions",
    "gaps",
}
DEGRADE_TARGETS = {
    "none",
    "assumptions",
    "human_approval_points",
    "gaps",
    "run_workflow_notes_for_wf_create_fast",
}
BLOCKING_SCOPES = {"approval", "handoff_target", "proposal_readability", "none"}


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


def _inventory_paths(index: dict[str, Any]) -> set[str]:
    files = index.get("files")
    if not isinstance(files, list):
        return set()
    return {
        str(item.get("path", "")).replace("\\", "/")
        for item in files
        if isinstance(item, dict) and str(item.get("path", "")).strip()
    }


def _validate_source_paths(
    values: Any,
    *,
    field: str,
    inventory_paths: set[str],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not isinstance(values, list) or not values:
        return [issue("MISSING_SOURCE_PATH", field, "来源路径必须是非空数组", "补充可在文件索引中定位的来源路径")]
    for index, value in enumerate(values):
        normalized = str(value or "").strip().replace("\\", "/")
        if not normalized or normalized not in inventory_paths:
            issues.append(
                issue(
                    "SOURCE_PATH_NOT_INDEXED",
                    f"{field}[{index}]",
                    f"来源路径未出现在 prompt_file_index：{normalized or '<empty>'}",
                    "改用索引中存在的源文件相对路径",
                )
            )
    return issues


def _validate_evidence_item(
    item: Any,
    *,
    field: str,
    required_fields: tuple[str, ...],
    inventory_paths: set[str],
) -> list[dict[str, Any]]:
    if not isinstance(item, dict):
        return [issue("INVALID_ITEM_TYPE", field, "条目必须是 JSON object", "按固定字段结构重写条目")]
    issues: list[dict[str, Any]] = []
    for key in required_fields:
        if key not in item:
            issues.append(issue("MISSING_REQUIRED_FIELD", f"{field}.{key}", "缺少必填字段", f"补充 {key}"))
    issues.extend(
        _validate_source_paths(
            item.get("source_files"),
            field=f"{field}.source_files",
            inventory_paths=inventory_paths,
        )
    )
    strength = item.get("evidence_strength")
    if strength not in EVIDENCE_STRENGTHS:
        issues.append(
            issue(
                "INVALID_EVIDENCE_STRENGTH",
                f"{field}.evidence_strength",
                "evidence_strength 必须是 high、medium 或 low",
                "按证据强弱选择固定枚举",
            )
        )
    consumers = item.get("proposal_consumer")
    if not isinstance(consumers, list) or not consumers or any(value not in PROPOSAL_CONSUMERS for value in consumers):
        issues.append(
            issue(
                "INVALID_PROPOSAL_CONSUMER",
                f"{field}.proposal_consumer",
                "proposal_consumer 必须是非空合法枚举数组",
                "明确该条目服务的 proposal 字段",
            )
        )
    degrade_target = item.get("degrade_target")
    if degrade_target not in DEGRADE_TARGETS:
        issues.append(
            issue(
                "INVALID_DEGRADE_TARGET",
                f"{field}.degrade_target",
                "degrade_target 不在允许枚举中",
                "明确证据不足时唯一的降级去向",
            )
        )
    if strength == "low" and degrade_target == "none":
        issues.append(
            issue(
                "LOW_EVIDENCE_WITHOUT_DEGRADE",
                f"{field}.degrade_target",
                "低证据条目不能声明无需降级",
                "降级到 assumptions、人工确认点或 gaps",
            )
        )
    if not str(item.get("evidence_summary", "")).strip():
        issues.append(
            issue(
                "MISSING_EVIDENCE_SUMMARY",
                f"{field}.evidence_summary",
                "缺少证据摘要",
                "概括来源文件中支持该结论的具体线索",
            )
        )
    return issues


def validate_inspection(inspection: dict[str, Any], index: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for key, expected_type in REQUIRED_TYPES.items():
        if key not in inspection:
            issues.append(issue("MISSING_REQUIRED_FIELD", key, "inspection 缺少必填字段", f"补充顶层字段 {key}"))
        elif not isinstance(inspection[key], expected_type):
            issues.append(
                issue(
                    "INVALID_FIELD_TYPE",
                    key,
                    f"{key} 必须是 {expected_type.__name__}",
                    f"按固定契约重写 {key}",
                )
            )
    if issues:
        return issues

    inventory_paths = _inventory_paths(index)
    if not inventory_paths:
        issues.append(issue("EMPTY_FILE_INDEX", "prompt_file_index.files", "文件索引为空或结构非法", "重新执行文件索引节点"))

    for item_index, item in enumerate(inspection["source_summary"]):
        field = f"source_summary[{item_index}]"
        if not isinstance(item, dict):
            issues.append(issue("INVALID_ITEM_TYPE", field, "source_summary 条目必须是对象", "补充 path、role 和 evidence"))
            continue
        for key in ("path", "role", "evidence"):
            if not str(item.get(key, "")).strip():
                issues.append(issue("MISSING_REQUIRED_FIELD", f"{field}.{key}", "字段不得为空", f"补充 {key}"))
        issues.extend(
            _validate_source_paths(
                [item.get("path")],
                field=f"{field}.path",
                inventory_paths=inventory_paths,
            )
        )

    stage_fields = (
        "stage_id",
        "name",
        "responsibility",
        "inputs",
        "outputs",
        "source_files",
        "evidence_strength",
        "proposal_consumer",
        "degrade_target",
        "evidence_summary",
    )
    for item_index, item in enumerate(inspection["detected_stages"]):
        issues.extend(
            _validate_evidence_item(
                item,
                field=f"detected_stages[{item_index}]",
                required_fields=stage_fields,
                inventory_paths=inventory_paths,
            )
        )

    prompt_fields = (
        "prompt_path",
        "responsibility",
        "inputs",
        "outputs",
        "constraints",
        "source_files",
        "evidence_strength",
        "proposal_consumer",
        "degrade_target",
        "evidence_summary",
    )
    for item_index, item in enumerate(inspection["prompt_contracts"]):
        issues.extend(
            _validate_evidence_item(
                item,
                field=f"prompt_contracts[{item_index}]",
                required_fields=prompt_fields,
                inventory_paths=inventory_paths,
            )
        )

    business_contract = inspection["source_business_contract"]
    for key in BUSINESS_CONTRACT_FIELDS:
        if key not in business_contract:
            issues.append(
                issue(
                    "MISSING_BUSINESS_CONTRACT_FIELD",
                    f"source_business_contract.{key}",
                    "业务契约缺少固定字段",
                    f"补充 {key}",
                )
            )
        elif key != "goal" and not isinstance(business_contract[key], list):
            issues.append(
                issue(
                    "INVALID_BUSINESS_CONTRACT_FIELD",
                    f"source_business_contract.{key}",
                    "业务契约集合字段必须是数组",
                    f"把 {key} 改为数组",
                )
            )

    seen_rule_ids: set[str] = set()
    for key in BUSINESS_CONTRACT_FIELDS[1:]:
        values = business_contract.get(key)
        if not isinstance(values, list):
            continue
        for item_index, item in enumerate(values):
            field = f"source_business_contract.{key}[{item_index}]"
            if not isinstance(item, dict):
                issues.append(issue("INVALID_BUSINESS_RULE", field, "业务规则条目必须是对象", "补充 rule_id、statement 和来源证据"))
                continue
            rule_id = str(item.get("rule_id", "")).strip()
            if not rule_id:
                issues.append(issue("MISSING_RULE_ID", f"{field}.rule_id", "业务规则缺少 rule_id", "为规则分配稳定唯一 ID"))
            elif rule_id in seen_rule_ids:
                issues.append(issue("DUPLICATE_RULE_ID", f"{field}.rule_id", f"重复 rule_id：{rule_id}", "为规则分配唯一 ID"))
            else:
                seen_rule_ids.add(rule_id)
            if not str(item.get("statement", "")).strip():
                issues.append(issue("MISSING_RULE_STATEMENT", f"{field}.statement", "业务规则缺少 statement", "补充可确认的业务陈述"))
            issues.extend(
                _validate_source_paths(
                    item.get("source_files"),
                    field=f"{field}.source_files",
                    inventory_paths=inventory_paths,
                )
            )
            if item.get("evidence_strength") != "high":
                issues.append(
                    issue(
                        "BUSINESS_RULE_NOT_HIGH_CONFIDENCE",
                        f"{field}.evidence_strength",
                        "source_business_contract 只允许高置信业务规则",
                        "补充证据，或把该条目降级到 assumptions/gaps",
                    )
                )

    for collection_name in ("gaps", "risks"):
        for item_index, item in enumerate(inspection[collection_name]):
            field = f"{collection_name}[{item_index}]"
            if not isinstance(item, dict):
                issues.append(issue("INVALID_ITEM_TYPE", field, f"{collection_name} 条目必须是对象", "按固定风险结构重写"))
                continue
            for key in ("id", "category", "description", "blocking_scope", "severity", "impact_chain"):
                if not str(item.get(key, "")).strip():
                    issues.append(issue("MISSING_REQUIRED_FIELD", f"{field}.{key}", "字段不得为空", f"补充 {key}"))
            if item.get("blocking_scope") not in BLOCKING_SCOPES:
                issues.append(issue("INVALID_BLOCKING_SCOPE", f"{field}.blocking_scope", "blocking_scope 枚举非法", "明确 approval、handoff_target、proposal_readability 或 none"))
            if item.get("severity") not in {"high", "medium", "low"}:
                issues.append(issue("INVALID_SEVERITY", f"{field}.severity", "severity 枚举非法", "改用 high、medium 或 low"))

    return issues


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    issues: list[dict[str, Any]]
    try:
        inspection = read_json_object(lgwf_dir / "prompt_workflow_inspection.json")
        index = read_json_object(lgwf_dir / "prompt_file_index.json")
        issues = validate_inspection(inspection, index)
    except (FileNotFoundError, json.JSONDecodeError, TypeError) as exc:
        issues = [issue("INVALID_INSPECTION_JSON", "prompt_workflow_inspection", f"inspection 或文件索引无法解析：{exc}", "重新执行 Act 或文件索引节点并输出合法 JSON")]
    report = build_observer_report(stage=STAGE, observer="python", issues=issues)
    write_json(lgwf_dir / "prompt_workflow_inspection_observe_py.json", report)
    print(json.dumps({"lgwf_wf_convert.inspect_python_observe": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
