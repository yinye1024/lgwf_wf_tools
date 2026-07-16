"""校验步骤设计 proposal 的结构契约。"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


def find_wf_root(start: Path) -> Path:
    for parent in start.resolve().parents:
        if parent.name == "wf":
            return parent
    return start.resolve().parents[3]


SHARED_SCRIPTS = find_wf_root(Path(__file__)) / "shared" / "scripts"
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
FORBIDDEN_SOURCE_FIELDS = ("content", "full_source", "source_code", "code", "body")
FORBIDDEN_GENERIC_CONTENT_TERMS = (
    "placeholder_result",
    "generated_result",
    "TODO",
    "LGWF_PLACEHOLDER",
    "_lgwf_placeholder",
    "待实现",
)
GENERIC_CONTRACT_PHRASES = (
    "由 workflow CONTRACT 声明",
    "由调用 workflow CONTRACT 或入口参数决定",
    "placeholder_result",
    "generated_result",
    "TODO",
    "待实现",
)
MAX_OBSERVATION_ISSUES = 80
REQUIRED_DIRECTORY_FIELDS = ("path", "purpose", "owner_step", "expected_files", "forbidden", "source_refs")
REQUIRED_FILE_FIELDS = (
    "path",
    "kind",
    "owner_step",
    "purpose",
    "required_structure",
    "reads",
    "writes",
    "dependencies",
    "acceptance_notes",
    "forbidden",
    "source_refs",
    "content_mode",
)
FILE_LIST_FIELDS = ("required_structure", "reads", "writes", "dependencies", "acceptance_notes", "forbidden", "source_refs")
DEFAULT_FORBIDDEN_CHANGES = [
    "不得写入 .lgwf/step_designs.json",
    "不得重新设计已确认 business_flow",
    "不得新增已确认步骤设计之外的实现目录结构",
    "不得输出完整源码字段",
]
REQUIRED_IMPLEMENTATION_FILE_DESIGNS = (
    "AGENTS.md",
    "README.md",
    "entry_contract.json",
    "wf/workflow.lgwf",
    "wf/artifact_contracts.json",
)
STAGE_WORKFLOW_PATTERN = re.compile(r"^wf/[^/]+/workflow\.lgwf$")
WORKFLOW_REFERENCE_PATTERN = re.compile(r'\b(SCRIPT|PROMPT|PROMPT_REF|SPEC|WORKFLOW)\s+"([^"]+)"')


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json_if_missing(path: Path, payload: dict[str, Any]) -> None:
    if not path.exists():
        write_json(path, payload)


def nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def check(name: str, passed: bool, message: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "message": message}


def failed_checks(result: dict[str, Any]) -> list[dict[str, Any]]:
    checks = result.get("checks")
    if not isinstance(checks, list):
        return []
    return [item for item in checks if isinstance(item, dict) and item.get("passed") is not True]


def structural_issues(result: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    for item in failed_checks(result):
        name = str(item.get("name", "structural_check_failed"))
        message = str(item.get("message", "结构校验失败"))
        issues.append(
            {
                "issue_id": name,
                "severity": "blocker",
                "evidence": message,
                "target_path": name,
                "required_change": message,
                "source": "structural_gate",
            }
        )
    return issues


def summarize_failed_checks(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_prefix: dict[str, int] = {}
    by_issue_type: dict[str, int] = {}
    for item in items:
        name = str(item.get("name", "structural_check_failed"))
        prefix = name.split("[", 1)[0].split("_", 1)[0] or "unknown"
        issue_type = name.rsplit("_", 1)[-1] if "_" in name else "other"
        by_prefix[prefix] = by_prefix.get(prefix, 0) + 1
        by_issue_type[issue_type] = by_issue_type.get(issue_type, 0) + 1
    return {
        "failed_count": len(items),
        "by_prefix": by_prefix,
        "by_issue_type": by_issue_type,
        "truncated_in_observation": len(items) > MAX_OBSERVATION_ISSUES,
        "max_observation_issues": MAX_OBSERVATION_ISSUES,
    }


def build_observation(result: dict[str, Any]) -> dict[str, Any]:
    blocking_issues = structural_issues(result)
    selected_issues = blocking_issues[:MAX_OBSERVATION_ISSUES]
    selected_failed_checks = failed_checks(result)[:MAX_OBSERVATION_ISSUES]
    issue_signatures = [
        str(issue.get("issue_id", ""))
        for issue in blocking_issues
        if str(issue.get("issue_id", "")).strip()
    ]
    passed = result.get("passed") is True and not blocking_issues
    return {
        "passed": passed,
        "verdict": "pass" if passed else "revise",
        "structural_passed": result.get("passed") is True,
        "issue_summary": summarize_failed_checks(failed_checks(result)),
        "blocking_issue_count": len(blocking_issues),
        "blocking_issues": selected_issues,
        "failed_checks": selected_failed_checks,
        "issue_signatures": issue_signatures,
        "reason_feedback": {
            "repair_mode": "targeted_repair" if not passed else "none",
            "priority_issue_ids": issue_signatures[:MAX_OBSERVATION_ISSUES],
            "must_preserve": [],
            "must_change": [
                {
                    "issue_id": issue["issue_id"],
                    "target": issue.get("target_path", ""),
                    "instruction": issue.get("required_change", issue.get("evidence", "")),
                }
                for issue in selected_issues
            ],
            "forbidden_changes": DEFAULT_FORBIDDEN_CHANGES,
            "act_instruction_patch": [],
        },
    }


def stable_json_hash(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def initial_decision_payload(observation: dict[str, Any], proposal_hash: str) -> tuple[dict[str, Any], dict[str, Any]]:
    passed = observation.get("passed") is True
    issue_signatures = [
        str(item).strip()
        for item in observation.get("issue_signatures", [])
        if str(item).strip()
    ] if isinstance(observation.get("issue_signatures"), list) else []
    analysis = {
        "recommended_next": "exit" if passed else "continue",
        "reason": "initial step design observation passed" if passed else "initial step design observation has blocking issues",
        "issue_signatures": issue_signatures,
        "repeat_issue_signatures": [],
        "no_progress_risk": False,
        "next_reason_feedback": observation.get("reason_feedback", {}),
        "source": "python_validate_step_designs_initial",
        "proposal_hash": proposal_hash,
    }
    decision = {
        "next": "exit" if passed else "continue",
        "passed": passed,
        "reason": analysis["reason"],
        "recommended_next": analysis["recommended_next"],
        "issue_signatures": issue_signatures,
        "repeat_issue_signatures": [],
        "no_progress_risk": False,
        "next_reason_feedback": analysis["next_reason_feedback"],
        "observation_file": ".lgwf/step_design_observation.json",
        "decision_analysis_file": ".lgwf/step_design_decision_analysis.json",
        "source": "python_decide_step_designs",
        "proposal_hash": proposal_hash,
    }
    return analysis, decision


def normalize_path_issue(raw_path: Any, *, allow_lgwf: bool = False) -> str:
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
    if not allow_lgwf and candidate.parts and candidate.parts[0] == ".lgwf":
        return "禁止指向 `.lgwf` 运行状态目录"
    return ""


def normalize_safe_path(raw_path: Any) -> str:
    return str(raw_path).strip().replace("\\", "/") if isinstance(raw_path, str) else ""


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip().replace("\\", "/") for item in value if str(item).strip()]


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def flattened_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(flattened_text(child) for child in value.values())
    if isinstance(value, list):
        return "\n".join(flattened_text(child) for child in value)
    return str(value) if value is not None else ""


def append_forbidden_text_checks(
    checks: list[dict[str, Any]],
    *,
    name_prefix: str,
    label: str,
    value: Any,
    forbidden_terms: tuple[str, ...],
) -> None:
    text_value = flattened_text(value)
    for term in forbidden_terms:
        checks.append(
            check(
                f"{name_prefix}_does_not_contain_{term}",
                term not in text_value,
                f"{label} 不得包含通用占位或兜底内容 `{term}`",
            )
        )


def strip_numeric_prefix(value: str) -> str:
    return re.sub(r"^\d+[_-]+", "", value.strip()).strip("_-")


def stage_contract_expectations(
    lgwf_dir: Path,
    confirmed_business_flow: dict[str, Any],
    scaffold_plan: dict[str, Any],
) -> tuple[set[str], list[dict[str, Any]]]:
    contract = load_json_object(lgwf_dir / "step_design_validation_contract.json")
    stage_identity = nested_dict(contract, "stage_identity")
    allowed_stage_ids = set(string_list(stage_identity.get("allowed_stage_ids")))
    required_stage_workflows = dict_list(contract.get("required_stage_workflows"))
    normalized_required: list[dict[str, Any]] = []
    for item in required_stage_workflows:
        workflow_ref = normalize_safe_path(item.get("workflow_ref"))
        stage_id = str(item.get("stage_id", "")).strip()
        aliases = string_list(item.get("aliases"))
        if workflow_ref and stage_id:
            normalized_required.append({"stage_id": stage_id, "workflow_ref": workflow_ref, "aliases": aliases})
            allowed_stage_ids.add(stage_id)
            allowed_stage_ids.update(aliases)
    if normalized_required:
        return allowed_stage_ids, normalized_required

    business_stage_ids = [
        str(item.get("stage_id", "")).strip()
        for item in dict_list(confirmed_business_flow.get("stages", []))
        if str(item.get("stage_id", "")).strip()
    ]
    workflow_to_stage = {
        normalize_safe_path(item.get("workflow_ref")): str(item.get("stage_id", "")).strip()
        for item in dict_list(confirmed_business_flow.get("stages", []))
        if normalize_safe_path(item.get("workflow_ref")) and str(item.get("stage_id", "")).strip()
    }
    allowed_stage_ids.update(business_stage_ids)
    for item in dict_list(scaffold_plan.get("stage_manifest", [])):
        scaffold_stage_id = str(item.get("stage_id", "")).strip()
        stage_dir = str(item.get("stage_dir", "")).strip() or scaffold_stage_id
        workflow_ref = normalize_safe_path(item.get("workflow_ref")) or (f"wf/{stage_dir}/workflow.lgwf" if stage_dir else "")
        stage_dir_alias = strip_numeric_prefix(stage_dir)
        stage_id = workflow_to_stage.get(workflow_ref) or (
            stage_dir_alias if stage_dir_alias in business_stage_ids else stage_dir if stage_dir in business_stage_ids else scaffold_stage_id
        )
        aliases = dedupe([scaffold_stage_id, stage_dir, stage_dir_alias])
        aliases = [alias for alias in aliases if alias and alias != stage_id]
        if stage_id:
            allowed_stage_ids.add(stage_id)
            allowed_stage_ids.update(aliases)
        if workflow_ref and stage_id:
            normalized_required.append({"stage_id": stage_id, "workflow_ref": workflow_ref, "aliases": aliases})
    if not normalized_required:
        for stage_id in business_stage_ids:
            normalized_required.append(
                {"stage_id": stage_id, "workflow_ref": f"wf/{stage_id}/workflow.lgwf", "aliases": []}
            )
    return allowed_stage_ids, normalized_required


def append_path_list_checks(checks: list[dict[str, Any]], index: int, field: str, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        checks.append(check(f"step_designs[{index}]_{field}_list", False, f"step_designs[{index}].{field} 必须是数组"))
        return
    checks.append(check(f"step_designs[{index}]_{field}_list", True, f"step_designs[{index}].{field} 是数组"))
    for item_index, item in enumerate(value):
        issue = normalize_path_issue(item, allow_lgwf=(field == "runtime_artifacts"))
        checks.append(
            check(
                f"step_designs[{index}]_{field}[{item_index}]_relative_safe",
                not issue,
                f"step_designs[{index}].{field}[{item_index}] {issue or '是安全相对路径'}",
            )
        )


def append_forbidden_source_field_checks(checks: list[dict[str, Any]], value: Any, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_SOURCE_FIELDS:
                checks.append(
                    check(
                        f"{path}_{key}_not_used",
                        False,
                        f"{path}.{key} 禁止承载完整源码；步骤设计只允许结构说明",
                    )
                )
            append_forbidden_source_field_checks(checks, child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            append_forbidden_source_field_checks(checks, child, f"{path}[{index}]")


def append_directory_design_checks(
    checks: list[dict[str, Any]],
    proposal: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    raw_items = proposal.get("directory_designs")
    if not isinstance(raw_items, list) or not raw_items:
        checks.append(check("directory_designs_present", False, "proposal.directory_designs 必须是非空数组"))
        return {}
    checks.append(check("directory_designs_present", True, "proposal.directory_designs 是非空数组"))
    designs: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            checks.append(check(f"directory_designs[{index}]_object", False, f"directory_designs[{index}] 必须是 object"))
            continue
        checks.append(check(f"directory_designs[{index}]_object", True, f"directory_designs[{index}] 是 object"))
        path = normalize_safe_path(item.get("path"))
        if path:
            duplicate = path in designs
            designs[path] = item
            issue = normalize_path_issue(path)
            checks.append(check(f"directory_designs[{index}]_path_relative_safe", not issue, f"directory_designs[{index}].path {issue or '是安全相对路径'}"))
            checks.append(check(f"directory_designs[{index}]_path_unique", not duplicate, f"directory_designs[{index}].path `{path}` {'重复' if duplicate else '唯一'}"))
        for field in REQUIRED_DIRECTORY_FIELDS:
            value = item.get(field)
            if field in {"expected_files", "forbidden", "source_refs"}:
                passed = isinstance(value, list) and bool(value)
                message = f"directory_designs[{index}].{field} 必须是非空数组"
            else:
                passed = isinstance(value, str) and bool(value.strip())
                message = f"directory_designs[{index}].{field} 必须是非空字符串"
            checks.append(check(f"directory_designs[{index}]_{field}_present", passed, message))
        expected_files = item.get("expected_files")
        if isinstance(expected_files, list):
            for file_index, raw_path in enumerate(expected_files):
                issue = normalize_path_issue(raw_path)
                checks.append(
                    check(
                        f"directory_designs[{index}]_expected_files[{file_index}]_relative_safe",
                        not issue,
                        f"directory_designs[{index}].expected_files[{file_index}] {issue or '是安全相对路径'}",
                    )
                )
    return designs


def append_file_design_type_checks(checks: list[dict[str, Any]], index: int, item: dict[str, Any]) -> None:
    path = normalize_safe_path(item.get("path"))
    required_text = "\n".join(str(value) for value in item.get("required_structure", []) if isinstance(value, str))
    acceptance_text = "\n".join(str(value) for value in item.get("acceptance_notes", []) if isinstance(value, str))
    combined = f"{required_text}\n{acceptance_text}"
    if path.endswith("workflow.lgwf"):
        for token in ("WORKFLOW", "ENTRY", "CONTRACT", "FLOW"):
            checks.append(
                check(
                    f"file_designs[{index}]_workflow_mentions_{token}",
                    token in combined,
                    f"file_designs[{index}] for workflow.lgwf 必须说明 {token}",
                )
            )
    if path.endswith("README.md") or path.endswith("AGENTS.md"):
        for token in ("定位", "输入", "输出", "验证", "禁止"):
            checks.append(
                check(
                    f"file_designs[{index}]_doc_mentions_{token}",
                    token in combined or token in str(item.get("purpose", "")),
                    f"file_designs[{index}] for {PurePosixPath(path).name} 必须说明{token}",
                )
            )
    if path.endswith(".py") or "/scripts/" in path:
        for token in ("入口", "读取", "写入", "错误", "UTF-8"):
            checks.append(
                check(
                    f"file_designs[{index}]_python_mentions_{token}",
                    token in combined,
                    f"file_designs[{index}] for Python 脚本必须说明{token}",
                )
            )
    if path.endswith(".json"):
        for token in ("顶层字段", "必填", "消费"):
            checks.append(
                check(
                    f"file_designs[{index}]_json_mentions_{token}",
                    token in combined,
                    f"file_designs[{index}] for JSON 文件必须说明{token}",
                )
            )


def append_file_design_content_contract_checks(checks: list[dict[str, Any]], index: int, item: dict[str, Any]) -> None:
    path = normalize_safe_path(item.get("path"))
    kind = str(item.get("kind", "")).strip()
    content_mode = str(item.get("content_mode", "")).strip()
    checks.append(
        check(
            f"file_designs[{index}]_content_mode_valid",
            content_mode in {"exact", "contract"},
            f"file_designs[{index}].content_mode 必须是 exact 或 contract",
        )
    )

    exact_content = item.get("exact_content")
    if kind in {"lgwf_workflow", "prompt"}:
        checks.append(
            check(
                f"file_designs[{index}]_{kind}_content_mode_exact",
                content_mode == "exact",
                f"file_designs[{index}] `{path}` 必须使用 content_mode=exact",
            )
        )
        checks.append(
            check(
                f"file_designs[{index}]_{kind}_exact_content_present",
                isinstance(exact_content, str) and bool(exact_content.strip()),
                f"file_designs[{index}] `{path}` 必须提供 exact_content",
            )
        )
        exact_text = exact_content if isinstance(exact_content, str) else ""
        append_forbidden_text_checks(
            checks,
            name_prefix=f"file_designs[{index}]_{kind}_exact_content",
            label=f"file_designs[{index}].exact_content",
            value=exact_text,
            forbidden_terms=FORBIDDEN_GENERIC_CONTENT_TERMS,
        )
        if kind == "lgwf_workflow":
            for token in ("WORKFLOW", "ENTRY", "CONTRACT", "FLOW"):
                checks.append(
                    check(
                        f"file_designs[{index}]_exact_workflow_contains_{token}",
                        token in exact_text,
                        f"file_designs[{index}].exact_content 必须包含 {token}",
                    )
                )
        if kind == "prompt":
            for token in ("Role", "Inputs", "Task", "Output", "Boundaries"):
                checks.append(
                    check(
                        f"file_designs[{index}]_exact_prompt_contains_{token}",
                        token in exact_text,
                        f"file_designs[{index}].exact_content 必须包含 {token}",
                    )
                )
        return

    checks.append(
        check(
            f"file_designs[{index}]_{kind or 'unknown'}_content_mode_contract",
            content_mode == "contract",
            f"file_designs[{index}] `{path}` 必须使用 content_mode=contract",
        )
    )
    if kind == "python_script":
        contract = item.get("script_contract")
        checks.append(
            check(
                f"file_designs[{index}]_script_contract_present",
                isinstance(contract, dict) and bool(contract),
                f"file_designs[{index}] `{path}` 必须提供 script_contract",
            )
        )
        if isinstance(contract, dict):
            for field in (
                "entrypoint",
                "input_files",
                "output_files",
                "required_functions",
                "behavior",
                "error_handling",
                "output_shape",
            ):
                value = contract.get(field)
                passed = bool(value) and (isinstance(value, str) or isinstance(value, list) or isinstance(value, dict))
                checks.append(
                    check(
                        f"file_designs[{index}]_script_contract_{field}_present",
                        passed,
                        f"file_designs[{index}].script_contract.{field} 必须存在",
                    )
                )
            behavior = contract.get("behavior")
            checks.append(
                check(
                    f"file_designs[{index}]_script_contract_behavior_specific",
                    isinstance(behavior, list)
                    and any(isinstance(item, str) and len(item.strip()) >= 12 for item in behavior)
                    and not any(term in flattened_text(behavior) for term in GENERIC_CONTRACT_PHRASES),
                    f"file_designs[{index}].script_contract.behavior 必须描述具体业务动作，不能是通用兜底",
                )
            )
            append_forbidden_text_checks(
                checks,
                name_prefix=f"file_designs[{index}]_script_contract",
                label=f"file_designs[{index}].script_contract",
                value=contract,
                forbidden_terms=FORBIDDEN_GENERIC_CONTENT_TERMS,
            )
    if kind == "markdown_doc":
        contract = item.get("markdown_contract")
        checks.append(
            check(
                f"file_designs[{index}]_markdown_contract_present",
                isinstance(contract, dict) and bool(contract),
                f"file_designs[{index}] `{path}` 必须提供 markdown_contract",
            )
        )
    if kind == "json_contract":
        contract = item.get("json_contract")
        checks.append(
            check(
                f"file_designs[{index}]_json_contract_present",
                isinstance(contract, dict) and bool(contract),
                f"file_designs[{index}] `{path}` 必须提供 json_contract",
            )
        )
    if kind == "test":
        contract = item.get("test_contract")
        checks.append(
            check(
                f"file_designs[{index}]_test_contract_present",
                isinstance(contract, dict) and bool(contract),
                f"file_designs[{index}] `{path}` 必须提供 test_contract",
            )
        )
        if isinstance(contract, dict):
            for field in ("test_framework", "scope", "fixtures", "acceptance"):
                value = contract.get(field)
                passed = bool(value) and (isinstance(value, str) or isinstance(value, list))
                checks.append(
                    check(
                        f"file_designs[{index}]_test_contract_{field}_present",
                        passed,
                        f"file_designs[{index}].test_contract.{field} 必须存在",
                    )
                )


def append_prompt_reference_checks(checks: list[dict[str, Any]], file_designs: dict[str, dict[str, Any]]) -> None:
    stage_workflows: dict[str, str] = {}
    for path, item in file_designs.items():
        if not STAGE_WORKFLOW_PATTERN.match(path):
            continue
        exact_content = item.get("exact_content")
        if isinstance(exact_content, str):
            parts = PurePosixPath(path).parts
            if len(parts) >= 3:
                stage_workflows[parts[1]] = exact_content

    for path, item in file_designs.items():
        if item.get("kind") != "prompt":
            continue
        parts = PurePosixPath(path).parts
        if len(parts) < 4 or parts[0] != "wf" or parts[2] != "agents":
            continue
        stage_dir = parts[1]
        prompt_ref = "/".join(parts[2:])
        workflow_text = stage_workflows.get(stage_dir, "")
        checks.append(
            check(
                f"prompt_referenced_by_stage_workflow_{path}",
                prompt_ref in workflow_text,
                f"`{path}` 必须被 `wf/{stage_dir}/workflow.lgwf` 的 exact_content 通过 `{prompt_ref}` 引用",
            )
        )


def workflow_reference_target(workflow_path: str, raw_ref: str) -> str:
    ref_path = normalize_safe_path(raw_ref)
    if not ref_path:
        return ""
    workflow_parent = PurePosixPath(workflow_path).parent
    if workflow_parent.as_posix() == ".":
        return ref_path
    return PurePosixPath(workflow_parent, ref_path).as_posix()


def append_workflow_exact_reference_checks(checks: list[dict[str, Any]], file_designs: dict[str, dict[str, Any]]) -> None:
    known_paths = set(file_designs)
    for path, item in file_designs.items():
        if item.get("kind") != "lgwf_workflow":
            continue
        exact_content = item.get("exact_content")
        if not isinstance(exact_content, str):
            continue
        for kind, raw_ref in WORKFLOW_REFERENCE_PATTERN.findall(exact_content):
            target = workflow_reference_target(path, raw_ref)
            checks.append(
                check(
                    f"workflow_exact_reference_exists_{path}_{kind}_{target}",
                    bool(target) and target in known_paths,
                    f"`{path}` exact_content 的 {kind} 引用 `{raw_ref}` 必须对应 file_designs `{target}`",
                )
            )


def append_file_design_checks(
    checks: list[dict[str, Any]],
    proposal: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    raw_items = proposal.get("file_designs")
    if not isinstance(raw_items, list) or not raw_items:
        checks.append(check("file_designs_present", False, "proposal.file_designs 必须是非空数组"))
        return {}
    checks.append(check("file_designs_present", True, "proposal.file_designs 是非空数组"))
    designs: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            checks.append(check(f"file_designs[{index}]_object", False, f"file_designs[{index}] 必须是 object"))
            continue
        checks.append(check(f"file_designs[{index}]_object", True, f"file_designs[{index}] 是 object"))
        path = normalize_safe_path(item.get("path"))
        if path:
            duplicate = path in designs
            designs[path] = item
            issue = normalize_path_issue(path)
            checks.append(check(f"file_designs[{index}]_path_relative_safe", not issue, f"file_designs[{index}].path {issue or '是安全相对路径'}"))
            checks.append(check(f"file_designs[{index}]_path_unique", not duplicate, f"file_designs[{index}].path `{path}` {'重复' if duplicate else '唯一'}"))
        for field in REQUIRED_FILE_FIELDS:
            value = item.get(field)
            if field in FILE_LIST_FIELDS:
                passed = isinstance(value, list) and bool(value)
                message = f"file_designs[{index}].{field} 必须是非空数组"
            else:
                passed = isinstance(value, str) and bool(str(value).strip())
                message = f"file_designs[{index}].{field} 必须是非空字符串"
            checks.append(check(f"file_designs[{index}]_{field}_present", passed, message))
        append_file_design_type_checks(checks, index, item)
        append_file_design_content_contract_checks(checks, index, item)
    return designs


def append_step_design_contract_checks(result: dict[str, Any], lgwf_dir: Path) -> dict[str, Any]:
    proposal = load_json_object(lgwf_dir / "step_designs_proposal.json")
    business_flow = load_json_object(lgwf_dir / "business_flow.json")
    scaffold = load_json_object(lgwf_dir / "scaffold_package_result.json")
    contract = load_json_object(lgwf_dir / "step_design_validation_contract.json")
    confirmed_business_flow = nested_dict(business_flow, "confirmed") or business_flow
    scaffold_plan = nested_dict(scaffold, "scaffold_plan") or scaffold
    expected_stage_ids, required_stage_workflows = stage_contract_expectations(
        lgwf_dir,
        confirmed_business_flow,
        scaffold_plan,
    )
    checks = result.setdefault("checks", [])
    append_forbidden_source_field_checks(checks, proposal, "proposal")
    directory_designs = append_directory_design_checks(checks, proposal)
    file_designs = append_file_design_checks(checks, proposal)
    append_prompt_reference_checks(checks, file_designs)
    append_workflow_exact_reference_checks(checks, file_designs)
    items = proposal.get("step_designs", [])
    if not isinstance(items, list) or not items:
        checks.append(check("step_designs_present", False, "proposal.step_designs 必须是非空数组"))
        result["passed"] = False
        return result
    checks.append(check("step_designs_present", True, "proposal.step_designs 是非空数组"))

    slugs: set[str] = set()
    referenced_files: set[str] = set()
    referenced_dirs: set[str] = set()
    stage_workflow_target_files: set[str] = set()
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
                    f"stage_id `{stage_id}` 必须匹配动态 step design contract 中允许的阶段 id 或别名",
                )
            )
        for field in OPTIONAL_LIST_PATH_FIELDS:
            append_path_list_checks(checks, index, field, item.get(field))
        for raw_file in item.get("target_files", []) if isinstance(item.get("target_files"), list) else []:
            path = normalize_safe_path(raw_file)
            if path:
                referenced_files.add(path)
                if STAGE_WORKFLOW_PATTERN.match(path):
                    stage_workflow_target_files.add(path)
                checks.append(
                    check(
                        f"step_designs[{index}]_target_file_has_design_{path}",
                        path in file_designs,
                        f"step_designs[{index}].target_files `{path}` 必须有对应 file_designs 条目",
                    )
                )
        for raw_dir in item.get("target_dirs", []) if isinstance(item.get("target_dirs"), list) else []:
            path = normalize_safe_path(raw_dir)
            if path:
                referenced_dirs.add(path)
                checks.append(
                    check(
                        f"step_designs[{index}]_target_dir_has_design_{path}",
                        path in directory_designs,
                        f"step_designs[{index}].target_dirs `{path}` 必须有对应 directory_designs 条目",
                    )
                )
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
    required_file_designs = dedupe(
        [
            *REQUIRED_IMPLEMENTATION_FILE_DESIGNS,
            *string_list(contract.get("required_file_designs")),
            *string_list(contract.get("scaffold_create_files")),
            *[
                normalize_safe_path(item.get("workflow_ref"))
                for item in required_stage_workflows
                if normalize_safe_path(item.get("workflow_ref"))
            ],
        ]
    )
    required_stage_workflow_refs = {
        normalize_safe_path(item.get("workflow_ref"))
        for item in required_stage_workflows
        if normalize_safe_path(item.get("workflow_ref"))
    }
    for workflow_ref in sorted(stage_workflow_target_files):
        checks.append(
            check(
                f"stage_workflow_target_file_allowed_{workflow_ref}",
                workflow_ref in required_stage_workflow_refs,
                f"`{workflow_ref}` 必须来自动态 step design contract 的 required_stage_workflows；不得额外生成非 canonical 兼容 workflow",
            )
        )
    for required_file in required_file_designs:
        checks.append(
            check(
                f"required_file_design_present_{required_file}",
                required_file in file_designs,
                f"file_designs 必须包含基础实现文件 `{required_file}`，04 不再从 scaffold 补齐",
            )
        )
        checks.append(
            check(
                f"required_file_design_referenced_{required_file}",
                required_file in referenced_files,
                f"`{required_file}` 必须被 step_designs[].target_files 引用，供 04 implementation units 消费",
            )
        )
    seen_stage_workflows: set[str] = set()
    for item in required_stage_workflows:
        expected_stage_id = str(item.get("stage_id", "")).strip()
        workflow_ref = normalize_safe_path(item.get("workflow_ref"))
        if not expected_stage_id or not workflow_ref or workflow_ref in seen_stage_workflows:
            continue
        seen_stage_workflows.add(workflow_ref)
        checks.append(
            check(
                f"stage_workflow_target_file_present_{expected_stage_id}",
                workflow_ref in stage_workflow_target_files,
                f"stage `{expected_stage_id}` 必须有 `{workflow_ref}` target_file，04 不再从 scaffold 推导阶段 workflow",
            )
        )
    for path in file_designs:
        checks.append(check(f"file_designs_path_referenced_{path}", path in referenced_files, f"file_designs `{path}` 必须被 step_designs[].target_files 引用"))
    for path in directory_designs:
        checks.append(check(f"directory_designs_path_referenced_{path}", path in referenced_dirs, f"directory_designs `{path}` 必须被 step_designs[].target_dirs 引用"))
    result["passed"] = all(item.get("passed") is True for item in checks)
    return result


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    proposal = load_json_object(lgwf_dir / "step_designs_proposal.json")
    proposal_hash = stable_json_hash(proposal)
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
    result["proposal_hash"] = proposal_hash
    observation = build_observation(result)
    observation["proposal_hash"] = proposal_hash
    analysis, decision = initial_decision_payload(observation, proposal_hash)
    write_json(lgwf_dir / "step_design_structural_gate.json", result)
    write_json(lgwf_dir / "step_design_observation.json", observation)
    write_json(lgwf_dir / "step_design_decision_analysis.json", analysis)
    write_json(lgwf_dir / "step_designs_proposal_decision.json", decision)
    print(
        json.dumps(
            {
                "lgwf_wf_create.step_design_structural_gate_summary": {
                    "passed": result.get("passed") is True,
                    "check_count": len(result.get("checks", [])) if isinstance(result.get("checks"), list) else 0,
                    "failed_count": len(failed_checks(result)),
                    "proposal_hash": proposal_hash,
                    "gate_file": ".lgwf/step_design_structural_gate.json",
                },
                "lgwf_wf_create.step_design_observation": observation,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
