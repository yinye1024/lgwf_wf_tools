"""规范化步骤设计 proposal 中可机械修复的结构问题。"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


FORBIDDEN_OUT_OF_SCOPE_TERMS = ("lgwf-wf-prompt-fix", "lgwf-wf-tools", "自动修复", "端到端运行保证")
FORBIDDEN_SOURCE_FIELDS = ("content", "full_source", "source_code", "code", "body")
REQUIRED_STEP_FIELDS = (
    "inputs",
    "outputs",
    "dependencies",
    "implementation_suggestions",
    "acceptance_notes",
    "out_of_scope",
    "confirmation_points",
    "target_files",
    "target_dirs",
    "runtime_artifacts",
    "source_refs",
    "risk_notes",
)
REQUIRED_FILE_LIST_FIELDS = ("required_structure", "reads", "writes", "dependencies", "acceptance_notes", "forbidden", "source_refs")
REQUIRED_DIRECTORY_LIST_FIELDS = ("expected_files", "forbidden", "source_refs")
STAGE_WORKFLOW_RE = re.compile(r"^wf/([^/]+)/workflow\.lgwf$")


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip().replace("\\", "/")
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return dedupe([str(item).strip() for item in value if str(item).strip()])


def normalize_safe_path(raw_path: Any, *, allow_lgwf: bool = False) -> str:
    value = text(raw_path).replace("\\", "/")
    if not value:
        return ""
    if value in (".", "./"):
        return "."
    value = value.strip().lstrip("/")
    if re.match(r"^[A-Za-z]:", value):
        value = value[2:].lstrip("/")
    if ":" in value:
        value = value.replace(":", "-")
    parts = [part for part in PurePosixPath(value).parts if part not in ("", ".")]
    cleaned: list[str] = []
    for part in parts:
        if part == "..":
            continue
        cleaned.append(part)
    if not allow_lgwf and cleaned and cleaned[0] == ".lgwf":
        cleaned = cleaned[1:]
    return "/".join(cleaned)


def remove_forbidden_source_fields(value: Any) -> bool:
    changed = False
    if isinstance(value, dict):
        for key in list(value.keys()):
            if key in FORBIDDEN_SOURCE_FIELDS:
                del value[key]
                changed = True
            else:
                changed = remove_forbidden_source_fields(value[key]) or changed
    elif isinstance(value, list):
        for item in value:
            changed = remove_forbidden_source_fields(item) or changed
    return changed


def ensure_list_field(item: dict[str, Any], field: str, fallback: str) -> bool:
    before = item.get(field)
    values = as_string_list(before)
    if not values:
        item[field] = [fallback]
        return before != item[field]
    item[field] = values
    return before != values


def ensure_text_field(item: dict[str, Any], field: str, fallback: str) -> bool:
    before = item.get(field)
    if isinstance(before, str) and before.strip():
        item[field] = before.strip()
        return before != item[field]
    item[field] = fallback
    return True


def append_missing_tokens(values: list[str], token_rules: list[tuple[str, str]]) -> tuple[list[str], bool]:
    combined = "\n".join(values)
    changed = False
    for token, sentence in token_rules:
        if token not in combined:
            values.append(sentence)
            changed = True
            combined += "\n" + sentence
    return values, changed


def infer_kind(path: str) -> str:
    if path.endswith("workflow.lgwf"):
        return "lgwf_workflow"
    if "/tests/" in path or path.startswith("tests/"):
        return "test"
    if "/agents/" in path:
        return "prompt"
    if path.endswith(".md"):
        return "markdown_doc"
    if path.endswith(".py"):
        return "python_script"
    if path.endswith(".json"):
        return "json_contract"
    if "/tests/" in path or path.startswith("tests/"):
        return "test"
    return "resource"


def owner_from_path(path: str, fallback_stage_id: str) -> str:
    match = STAGE_WORKFLOW_RE.match(path)
    if match:
        return match.group(1)
    parts = PurePosixPath(path).parts
    if len(parts) >= 2 and parts[0] == "wf":
        return parts[1]
    return fallback_stage_id or "package_contracts"


def safe_identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_")
    if not cleaned:
        cleaned = fallback
    if not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"stage_{cleaned}"
    return cleaned


def fallback_exact_workflow(path: str) -> str:
    workflow_id = safe_identifier(path.removesuffix("/workflow.lgwf").replace("/", "_"), "generated_workflow")
    return (
        f"WORKFLOW {workflow_id};\n"
        "ENTRY run_stage;\n\n"
        "PY run_stage\n"
        '  SCRIPT "scripts/run.py"\n'
        "  CONTRACT {\n"
        '    WRITE workspace file ".lgwf/generated_result.json";\n'
        "  };\n\n"
        "FLOW run_stage;\n"
    )


def ensure_content_contract(item: dict[str, Any], path: str, kind: str) -> bool:
    changed = False
    if kind in {"lgwf_workflow", "prompt"}:
        if item.get("content_mode") != "exact":
            item["content_mode"] = "exact"
            changed = True
        if not text(item.get("exact_content")):
            if kind == "lgwf_workflow":
                item["exact_content"] = fallback_exact_workflow(path)
            else:
                item["exact_content"] = (
                    "# agent prompt\n\n"
                    "## Role\n待实现阶段 agent。\n\n"
                    "## Inputs\n只读取 CONTRACT 声明的输入。\n\n"
                    "## Output\n写入 CONTRACT 声明的输出。\n\n"
                    "## Boundaries\n不得扩大读取或写入范围。\n"
                )
            changed = True
        return changed

    if item.get("content_mode") != "contract":
        item["content_mode"] = "contract"
        changed = True
    if kind == "python_script" and not isinstance(item.get("script_contract"), dict):
        item["script_contract"] = {
            "entrypoint": "main()",
            "input_files": ["由 workflow CONTRACT 声明"],
            "output_files": ["由 workflow CONTRACT 声明"],
            "required_functions": ["load_json", "write_json", "run", "main"],
            "error_handling": ["输入缺失或解析失败时返回结构化错误。"],
        }
        changed = True
    if kind == "test" and not isinstance(item.get("test_contract"), dict):
        item["test_contract"] = {
            "test_framework": "Python unittest",
            "scope": ["关键文件存在性、路径边界和最小 DSL 结构。"],
            "fixtures": ["使用隔离临时目录，不依赖本机绝对路径。"],
            "acceptance": ["测试失败信息必须指向具体缺失文件或结构问题。"],
        }
        changed = True
    if kind == "markdown_doc" and not isinstance(item.get("markdown_contract"), dict):
        item["markdown_contract"] = {
            "sections": ["模块定位", "入口", "输入", "输出", "验证", "禁止事项"],
        }
        changed = True
    if kind == "json_contract" and not isinstance(item.get("json_contract"), dict):
        item["json_contract"] = {
            "top_level_fields": ["status", "data", "errors"],
            "required": ["status"],
            "consumer": "下游 workflow 节点或测试",
        }
        changed = True
    return changed


def normalize_file_design(item: dict[str, Any], fallback_stage_id: str) -> bool:
    changed = False
    path = normalize_safe_path(item.get("path"))
    if path != item.get("path"):
        item["path"] = path
        changed = True
    changed = ensure_text_field(item, "kind", infer_kind(path)) or changed
    kind = text(item.get("kind"))
    changed = ensure_text_field(item, "owner_step", owner_from_path(path, fallback_stage_id)) or changed
    changed = ensure_text_field(item, "purpose", f"定义 `{path}` 的职责、结构和验收边界。") or changed
    for field in REQUIRED_FILE_LIST_FIELDS:
        changed = ensure_list_field(item, field, f"{path} 的 {field} 由已确认步骤设计消费。") or changed

    required_structure = as_string_list(item.get("required_structure"))
    acceptance_notes = as_string_list(item.get("acceptance_notes"))
    if path.endswith("workflow.lgwf"):
        required_structure, token_changed = append_missing_tokens(
            required_structure,
            [
                ("WORKFLOW", "必须声明 WORKFLOW 名称。"),
                ("ENTRY", "必须声明 ENTRY 入口。"),
                ("CONTRACT", "必须声明 CONTRACT 读写契约。"),
                ("FLOW", "必须声明 FLOW 执行顺序。"),
            ],
        )
        changed = token_changed or changed
    if path.endswith("README.md") or path.endswith("AGENTS.md"):
        required_structure, token_changed = append_missing_tokens(
            required_structure,
            [
                ("定位", "必须说明模块定位。"),
                ("输入", "必须说明输入。"),
                ("输出", "必须说明输出。"),
                ("验证", "必须说明验证方式。"),
                ("禁止", "必须说明禁止事项。"),
            ],
        )
        changed = token_changed or changed
    if path.endswith(".py") or "/scripts/" in path:
        required_structure, token_changed = append_missing_tokens(
            required_structure,
            [
                ("入口", "必须说明入口函数或 CLI 入口。"),
                ("读取", "必须说明读取的文件或状态。"),
                ("写入", "必须说明写入的文件或状态。"),
                ("错误", "必须说明错误处理策略。"),
                ("UTF-8", "必须说明 UTF-8 JSON 读写要求。"),
            ],
        )
        changed = token_changed or changed
    if path.endswith(".json"):
        required_structure, token_changed = append_missing_tokens(
            required_structure,
            [
                ("顶层字段", "必须说明顶层字段。"),
                ("必填", "必须说明必填字段。"),
                ("消费", "必须说明消费方。"),
            ],
        )
        changed = token_changed or changed

    item["required_structure"] = required_structure
    item["acceptance_notes"] = acceptance_notes
    if not as_string_list(item.get("reads")):
        item["reads"] = [f"实现阶段读取 `{path}` 的 file_design。"]
        changed = True
    if not as_string_list(item.get("writes")):
        item["writes"] = [f"实现阶段写入 `{path}`。"]
        changed = True
    if not as_string_list(item.get("dependencies")):
        item["dependencies"] = ["依赖已确认 requirements、business_flow、scaffold plan 和动态 step design contract。"]
        changed = True
    if not as_string_list(item.get("forbidden")):
        item["forbidden"] = ["不得承载完整源码字段。"]
        changed = True
    if not as_string_list(item.get("source_refs")):
        item["source_refs"] = ["step_design_validation_contract"]
        changed = True
    changed = ensure_content_contract(item, path, kind) or changed
    return changed


def normalize_directory_design(item: dict[str, Any], file_paths: set[str], fallback_stage_id: str) -> bool:
    changed = False
    path = normalize_safe_path(item.get("path"))
    if not path:
        path = "."
    if path != item.get("path"):
        item["path"] = path
        changed = True
    changed = ensure_text_field(item, "purpose", f"承载 `{path}` 相关文件。") or changed
    changed = ensure_text_field(item, "owner_step", owner_from_path(f"{path}/workflow.lgwf", fallback_stage_id)) or changed
    for field in REQUIRED_DIRECTORY_LIST_FIELDS:
        changed = ensure_list_field(item, field, f"{path} 的 {field} 由已确认步骤设计消费。") or changed
    expected_files = [normalize_safe_path(value) for value in as_string_list(item.get("expected_files"))]
    expected_files = [value for value in expected_files if value]
    if not expected_files:
        prefix = "" if path == "." else f"{path}/"
        expected_files = sorted(candidate for candidate in file_paths if candidate.startswith(prefix))[:5]
    if not expected_files:
        expected_files = [f"{path}/README.md" if path else "README.md"]
    item["expected_files"] = dedupe(expected_files)
    return changed


def load_stage_rules(contract: dict[str, Any]) -> tuple[list[str], dict[str, str], dict[str, str]]:
    stage_identity = contract.get("stage_identity") if isinstance(contract.get("stage_identity"), dict) else {}
    canonical = as_string_list(stage_identity.get("canonical_stage_ids"))
    aliases_raw = stage_identity.get("stage_aliases")
    aliases = {str(key): str(value) for key, value in aliases_raw.items()} if isinstance(aliases_raw, dict) else {}
    workflow_to_stage = {}
    for item in contract.get("required_stage_workflows", []):
        if not isinstance(item, dict):
            continue
        workflow_ref = normalize_safe_path(item.get("workflow_ref"))
        stage_id = text(item.get("stage_id"))
        if workflow_ref and stage_id:
            workflow_to_stage[workflow_ref] = stage_id
            if stage_id not in canonical:
                canonical.append(stage_id)
    return dedupe(canonical), aliases, workflow_to_stage


def infer_stage_id(item: dict[str, Any], canonical_stage_ids: list[str], aliases: dict[str, str], workflow_to_stage: dict[str, str]) -> str:
    raw_stage_id = text(item.get("stage_id"))
    if raw_stage_id in canonical_stage_ids:
        return raw_stage_id
    if raw_stage_id in aliases:
        return aliases[raw_stage_id]
    target_files = as_string_list(item.get("target_files"))
    for path in target_files:
        normalized = normalize_safe_path(path)
        if normalized in workflow_to_stage:
            return workflow_to_stage[normalized]
    for path in target_files:
        for workflow_ref, stage_id in workflow_to_stage.items():
            stage_dir = PurePosixPath(workflow_ref).parts[1] if len(PurePosixPath(workflow_ref).parts) > 2 else ""
            if stage_dir and path.startswith(f"wf/{stage_dir}/"):
                return stage_id
    if canonical_stage_ids:
        return canonical_stage_ids[0]
    return raw_stage_id or "package_contracts"


def normalize_runtime_artifact(raw_value: str, index: int) -> str:
    value = normalize_safe_path(raw_value, allow_lgwf=True)
    if not value:
        return f".lgwf/step_design_runtime_artifact_{index}.json"
    if value.startswith("work dir runtime state-"):
        suffix = value.removeprefix("work dir runtime state-").strip("/") or f"state_{index}.json"
        return f".lgwf/{suffix}"
    if value.startswith("work dir report-"):
        suffix = value.removeprefix("work dir report-").strip("/") or f"report_{index}.json"
        return f"reports/{suffix}"
    if value.startswith("stdout "):
        return f".lgwf/stdout_{index}.txt"
    return value


def normalize_step_design(
    item: dict[str, Any],
    canonical_stage_ids: list[str],
    aliases: dict[str, str],
    workflow_to_stage: dict[str, str],
) -> bool:
    changed = False
    stage_id = infer_stage_id(item, canonical_stage_ids, aliases, workflow_to_stage)
    if item.get("stage_id") != stage_id:
        item["stage_id"] = stage_id
        changed = True
    changed = ensure_text_field(item, "step_slug", text(item.get("step_slug")) or stage_id or "step_design") or changed
    changed = ensure_text_field(item, "step_name", text(item.get("step_name")) or text(item.get("step_slug")) or stage_id) or changed
    changed = ensure_text_field(item, "goal", text(item.get("goal")) or f"设计 `{stage_id}` 阶段的目标文件、目录和产物。") or changed
    for field in REQUIRED_STEP_FIELDS:
        changed = ensure_list_field(item, field, f"{field} 由已确认 requirements、business_flow、scaffold plan 和动态 contract 推导。") or changed

    out_of_scope = as_string_list(item.get("out_of_scope"))
    for term in FORBIDDEN_OUT_OF_SCOPE_TERMS:
        if term not in "\n".join(out_of_scope):
            out_of_scope.append(f"不处理 {term}。")
            changed = True
    item["out_of_scope"] = out_of_scope

    target_files = [normalize_safe_path(path) for path in as_string_list(item.get("target_files"))]
    target_dirs = [normalize_safe_path(path) for path in as_string_list(item.get("target_dirs"))]
    runtime_artifacts = [
        normalize_runtime_artifact(path, index)
        for index, path in enumerate(as_string_list(item.get("runtime_artifacts")))
    ]
    item["target_files"] = dedupe([path for path in target_files if path])
    item["target_dirs"] = dedupe([path for path in target_dirs if path])
    item["runtime_artifacts"] = dedupe([path for path in runtime_artifacts if path])
    return changed


def ensure_required_file_designs(proposal: dict[str, Any], contract: dict[str, Any], fallback_stage_id: str) -> int:
    required_files = as_string_list(contract.get("required_file_designs"))
    file_designs = proposal.setdefault("file_designs", [])
    if not isinstance(file_designs, list):
        file_designs = []
        proposal["file_designs"] = file_designs
    existing = {
        normalize_safe_path(item.get("path")): item
        for item in file_designs
        if isinstance(item, dict) and normalize_safe_path(item.get("path"))
    }
    added = 0
    for path in required_files:
        normalized = normalize_safe_path(path)
        if not normalized or normalized in existing:
            continue
        item: dict[str, Any] = {"path": normalized}
        normalize_file_design(item, fallback_stage_id)
        file_designs.append(item)
        existing[normalized] = item
        added += 1
    return added


def ensure_required_stage_steps(proposal: dict[str, Any], contract: dict[str, Any]) -> int:
    step_designs = proposal.setdefault("step_designs", [])
    if not isinstance(step_designs, list):
        step_designs = []
        proposal["step_designs"] = step_designs
    existing_files = {
        normalize_safe_path(path)
        for item in step_designs
        if isinstance(item, dict)
        for path in as_string_list(item.get("target_files"))
    }
    added = 0
    for item in contract.get("required_stage_workflows", []):
        if not isinstance(item, dict):
            continue
        workflow_ref = normalize_safe_path(item.get("workflow_ref"))
        stage_id = text(item.get("stage_id"))
        if not workflow_ref or workflow_ref in existing_files:
            continue
        stage_dir = PurePosixPath(workflow_ref).parts[1] if len(PurePosixPath(workflow_ref).parts) > 2 else stage_id
        step = {
            "step_slug": stage_id or stage_dir,
            "step_name": f"设计 {stage_id or stage_dir} 阶段 workflow",
            "stage_id": stage_id,
            "goal": f"补齐 `{workflow_ref}` 的步骤设计覆盖。",
            "inputs": ["已确认 business_flow", "动态 step design contract"],
            "outputs": [workflow_ref],
            "dependencies": ["根 workflow 编排", "scaffold plan"],
            "implementation_suggestions": ["阶段 workflow 必须声明节点、CONTRACT 和 FLOW。"],
            "acceptance_notes": ["阶段 workflow 必须被 target_files 覆盖，并拥有 file_design。"],
            "out_of_scope": [f"不处理 {term}。" for term in FORBIDDEN_OUT_OF_SCOPE_TERMS],
            "confirmation_points": ["确认阶段 workflow 的输入、输出和产物。"],
            "target_files": [workflow_ref],
            "target_dirs": [f"wf/{stage_dir}"],
            "runtime_artifacts": [f".lgwf/{stage_id or stage_dir}_result.json"],
            "source_refs": ["step_design_validation_contract.required_stage_workflows"],
            "risk_notes": ["阶段 id 必须与已确认业务流一致。"],
        }
        step_designs.append(step)
        existing_files.add(workflow_ref)
        added += 1
    return added


def ensure_directory_designs_for_targets(proposal: dict[str, Any], fallback_stage_id: str) -> int:
    directory_designs = proposal.setdefault("directory_designs", [])
    if not isinstance(directory_designs, list):
        directory_designs = []
        proposal["directory_designs"] = directory_designs
    file_paths = {
        normalize_safe_path(item.get("path"))
        for item in proposal.get("file_designs", [])
        if isinstance(item, dict) and normalize_safe_path(item.get("path"))
    }
    target_dirs = {
        normalize_safe_path(path)
        for item in proposal.get("step_designs", [])
        if isinstance(item, dict)
        for path in as_string_list(item.get("target_dirs"))
    }
    existing = {
        normalize_safe_path(item.get("path")): item
        for item in directory_designs
        if isinstance(item, dict) and normalize_safe_path(item.get("path"))
    }
    added = 0
    for path in sorted(target_dirs):
        if not path or path in existing:
            continue
        item = {"path": path}
        normalize_directory_design(item, file_paths, fallback_stage_id)
        directory_designs.append(item)
        existing[path] = item
        added += 1
    return added


def ensure_all_designs_referenced(proposal: dict[str, Any], fallback_stage_id: str) -> bool:
    step_designs = [item for item in proposal.get("step_designs", []) if isinstance(item, dict)]
    if not step_designs:
        return False
    owner = step_designs[0]
    referenced_files = {
        normalize_safe_path(path)
        for item in step_designs
        for path in as_string_list(item.get("target_files"))
    }
    referenced_dirs = {
        normalize_safe_path(path)
        for item in step_designs
        for path in as_string_list(item.get("target_dirs"))
    }
    all_files = {
        normalize_safe_path(item.get("path"))
        for item in proposal.get("file_designs", [])
        if isinstance(item, dict) and normalize_safe_path(item.get("path"))
    }
    all_dirs = {
        normalize_safe_path(item.get("path"))
        for item in proposal.get("directory_designs", [])
        if isinstance(item, dict) and normalize_safe_path(item.get("path"))
    }
    missing_files = sorted(all_files - referenced_files)
    missing_dirs = sorted(all_dirs - referenced_dirs)
    if not missing_files and not missing_dirs:
        return False
    owner["target_files"] = dedupe(as_string_list(owner.get("target_files")) + missing_files)
    owner["target_dirs"] = dedupe(as_string_list(owner.get("target_dirs")) + missing_dirs)
    if not text(owner.get("stage_id")):
        owner["stage_id"] = fallback_stage_id
    return True


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    proposal_path = lgwf_dir / "step_designs_proposal.json"
    contract_path = lgwf_dir / "step_design_validation_contract.json"
    proposal = load_json_object(proposal_path)
    contract = load_json_object(contract_path)
    canonical_stage_ids, aliases, workflow_to_stage = load_stage_rules(contract)
    fallback_stage_id = canonical_stage_ids[0] if canonical_stage_ids else "package_contracts"

    changes: list[str] = []
    if remove_forbidden_source_fields(proposal):
        changes.append("removed_forbidden_source_fields")

    for field in ("workflow_id", "workflow_name", "target_package_root", "package_profile"):
        identity = contract.get("identity") if isinstance(contract.get("identity"), dict) else {}
        if not text(proposal.get(field)) and text(identity.get(field)):
            proposal[field] = text(identity.get(field))
            changes.append(f"filled_{field}")

    if not as_string_list(proposal.get("source_business_flow_stages")):
        proposal["source_business_flow_stages"] = canonical_stage_ids or [fallback_stage_id]
        changes.append("filled_source_business_flow_stages")
    if not as_string_list(proposal.get("design_rationale")):
        proposal["design_rationale"] = ["步骤设计按 schema、动态 contract、已确认 business_flow 和 scaffold plan 收敛。"]
        changes.append("filled_design_rationale")

    added_required_files = ensure_required_file_designs(proposal, contract, fallback_stage_id)
    if added_required_files:
        changes.append(f"added_required_file_designs:{added_required_files}")
    added_stage_steps = ensure_required_stage_steps(proposal, contract)
    if added_stage_steps:
        changes.append(f"added_required_stage_steps:{added_stage_steps}")

    step_designs = proposal.get("step_designs")
    if not isinstance(step_designs, list) or not step_designs:
        proposal["step_designs"] = [
            {
                "step_slug": fallback_stage_id,
                "step_name": f"设计 {fallback_stage_id}",
                "stage_id": fallback_stage_id,
                "goal": "补齐步骤设计 proposal 的基础 step。",
                "inputs": ["已确认 requirements"],
                "outputs": ["步骤设计 proposal"],
                "dependencies": ["动态 step design contract"],
                "implementation_suggestions": ["按 schema 填写 file_designs、directory_designs 和 step_designs。"],
                "acceptance_notes": ["proposal 必须通过结构校验。"],
                "out_of_scope": [f"不处理 {term}。" for term in FORBIDDEN_OUT_OF_SCOPE_TERMS],
                "confirmation_points": ["确认步骤设计覆盖范围。"],
                "target_files": [],
                "target_dirs": [],
                "runtime_artifacts": [".lgwf/step_designs_proposal.json"],
                "source_refs": ["step_design_validation_contract"],
                "risk_notes": ["自动补齐内容仍需人工 review。"],
            }
        ]
        changes.append("created_fallback_step_design")

    for item in proposal.get("step_designs", []):
        if isinstance(item, dict) and normalize_step_design(item, canonical_stage_ids, aliases, workflow_to_stage):
            changes.append(f"normalized_step:{text(item.get('step_slug'))}")

    file_designs = proposal.get("file_designs")
    if not isinstance(file_designs, list):
        proposal["file_designs"] = []
        file_designs = proposal["file_designs"]
        changes.append("created_file_designs")
    for item in file_designs:
        if isinstance(item, dict) and normalize_file_design(item, fallback_stage_id):
            changes.append(f"normalized_file:{text(item.get('path'))}")

    if ensure_directory_designs_for_targets(proposal, fallback_stage_id):
        changes.append("added_missing_directory_designs")
    file_paths = {
        normalize_safe_path(item.get("path"))
        for item in proposal.get("file_designs", [])
        if isinstance(item, dict) and normalize_safe_path(item.get("path"))
    }
    for item in proposal.get("directory_designs", []):
        if isinstance(item, dict) and normalize_directory_design(item, file_paths, fallback_stage_id):
            changes.append(f"normalized_dir:{text(item.get('path'))}")

    if ensure_all_designs_referenced(proposal, fallback_stage_id):
        changes.append("referenced_unowned_designs")

    write_json(proposal_path, proposal)
    report = {
        "changed": bool(changes),
        "changes": changes,
        "proposal_file": ".lgwf/step_designs_proposal.json",
        "contract_file": ".lgwf/step_design_validation_contract.json",
    }
    write_json(lgwf_dir / "step_design_normalization_report.json", report)
    print(json.dumps({"lgwf_wf_create.step_design_normalization": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
