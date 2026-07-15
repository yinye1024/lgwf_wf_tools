"""基于已确认输入确定性生成步骤设计 proposal。"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


OUT_OF_SCOPE = (
    "不处理 lgwf-wf-prompt-fix。",
    "不修改 lgwf-wf-tools。",
    "不执行自动修复。",
    "不承诺端到端运行保证。",
)
ROOT_CONTRACT_FILES = (
    "SKILL.md",
    "AGENTS.md",
    "README.md",
    "entry_contract.json",
    "wf/workflow.lgwf",
    "wf/artifact_contracts.json",
)


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip().replace("\\", "/") for item in value if str(item).strip()]


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


def safe_path(value: str) -> str:
    raw = value.strip().replace("\\", "/")
    if raw == ".":
        return "."
    if raw.startswith("/"):
        raw = raw.lstrip("/")
    if len(raw) >= 2 and raw[1] == ":":
        raw = raw[2:].lstrip("/")
    parts = [part for part in PurePosixPath(raw).parts if part not in ("", ".")]
    return "/".join(part for part in parts if part != "..")


def parent_dirs(path: str) -> list[str]:
    pure = PurePosixPath(path)
    dirs: list[str] = []
    current = pure.parent
    while current.as_posix() not in ("", "."):
        dirs.append(current.as_posix())
        current = current.parent
    return list(reversed(dirs))


def stage_dir_from_workflow_ref(workflow_ref: str, fallback: str) -> str:
    parts = PurePosixPath(workflow_ref).parts
    if len(parts) >= 3 and parts[0] == "wf":
        return parts[1]
    return fallback


def stage_slug(stage_id: str) -> str:
    return stage_id.replace(" ", "_").replace("/", "_")


def safe_lgwf_identifier(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_")
    if not cleaned:
        cleaned = fallback
    if not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"stage_{cleaned}"
    return cleaned


def file_kind(path: str) -> str:
    if path.endswith("workflow.lgwf"):
        return "lgwf_workflow"
    if path.startswith("tests/") or "/tests/" in path:
        return "test"
    if "/agents/" in path:
        return "prompt"
    if path.endswith(".py"):
        return "python_script"
    if path.endswith(".json"):
        return "json_contract"
    if path.endswith(".md"):
        return "markdown_doc"
    return "resource"


def is_stage_artifact_contract(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return len(parts) == 3 and parts[0] == "wf" and parts[2] == "artifact_contracts.json"


def file_owner(path: str, stage_by_dir: dict[str, str]) -> str:
    parts = PurePosixPath(path).parts
    if len(parts) >= 2 and parts[0] == "wf" and parts[1] in stage_by_dir:
        return stage_by_dir[parts[1]]
    if path in ROOT_CONTRACT_FILES:
        return "package_contracts"
    if path.startswith("tests/"):
        return "shared_helpers_tests"
    if path.startswith("scripts/"):
        return "shared_helpers_tests"
    return "package_contracts"


def file_required_structure(path: str, kind: str) -> list[str]:
    if is_stage_artifact_contract(path):
        return [
            "必须声明 bootstrap_inputs 和 final_outputs。",
            "bootstrap_inputs 必须覆盖本 stage workflow CONTRACT 中读取、但由上游 stage 生产的 workspace artifact。",
            "final_outputs 必须覆盖本 stage workflow CONTRACT 中写入、但在该 stage 内部没有下游读取的 workspace artifact。",
            "必须能支撑 `lgwf.py audit wf/<stage>/workflow.lgwf` 单独通过。",
        ]
    if path == "wf/artifact_contracts.json":
        return [
            "必须声明 bootstrap_inputs、final_outputs、script_writes、runtime_records、delivery_artifacts 和 pending_confirmations。",
            "必须覆盖根 workflow 下所有跨 stage workspace handoff 和最终交付产物。",
            "必须能支撑 `lgwf.py audit wf/workflow.lgwf` 通过。",
        ]
    if kind == "lgwf_workflow":
        return [
            "必须声明 WORKFLOW 名称。",
            "必须声明 ENTRY 入口节点。",
            "必须为读写文件或 state 的节点声明 CONTRACT。",
            "必须声明 FLOW 顺序，根 workflow 只编排阶段，阶段 workflow 编排本阶段节点。",
        ]
    if kind == "markdown_doc":
        return [
            "必须说明模块定位。",
            "必须说明入口、输入和输出。",
            "必须说明状态边界、产物、验证和禁止事项。",
        ]
    if kind == "python_script":
        return [
            "必须说明入口函数或 CLI 入口。",
            "必须说明读取文件和写入文件。",
            "必须说明错误处理策略。",
            "必须使用 UTF-8 JSON 读写。",
        ]
    if kind == "json_contract":
        return [
            "必须说明顶层字段。",
            "必须说明必填字段。",
            "必须说明消费方和生产方。",
        ]
    if kind == "prompt":
        return [
            "必须说明 role、inputs、task、output 和 boundaries。",
            "不得要求读取目标源码或运行态目录之外的非契约上下文。",
        ]
    if kind == "test":
        return [
            "必须覆盖关键文件存在性、路径边界和最小行为。",
            "不得依赖本机绝对路径。",
        ]
    return ["必须说明文件职责、结构轮廓和验收边界。"]


def file_acceptance_notes(path: str, kind: str) -> list[str]:
    notes = [f"`{path}` 必须由实现阶段生成并保持 UTF-8 no BOM。"]
    if is_stage_artifact_contract(path):
        notes.append("stage 级 artifact_contracts.json 必须用 package-root 为该 stage 目录的视角声明 bootstrap_inputs/final_outputs。")
    if path == "wf/artifact_contracts.json":
        notes.append("根 artifact_contracts.json 必须用 package-root 为 `wf/` 的视角声明跨 stage handoff 和最终输出。")
    if kind == "lgwf_workflow":
        notes.append("workflow.lgwf 必须声明 WORKFLOW、ENTRY、CONTRACT 和 FLOW。")
    if kind == "json_contract":
        notes.append("JSON 文件必须可解析，并说明顶层字段、必填字段和消费方。")
    if kind == "markdown_doc":
        notes.append("文档必须覆盖定位、输入、输出、验证和禁止事项。")
    if kind == "python_script":
        notes.append("脚本必须说明入口、读取、写入、错误处理和 UTF-8 JSON 读写。")
    return notes


def workspace_artifacts_from_values(values: Any) -> list[str]:
    artifacts: list[str] = []
    for value in string_list(values):
        normalized = value.strip().strip("`'\"“”‘’，,。；;：:（）()[]{}<>").replace("\\", "/")
        if normalized.startswith("ws/"):
            normalized = normalized.removeprefix("ws/")
        if normalized.startswith(".lgwf/") or normalized.startswith("reports/"):
            artifacts.append(normalized)
    return dedupe(artifacts)


def stage_runtime_artifact(stage_id: str) -> str:
    safe_stage = stage_slug(stage_id) or "stage"
    return f".lgwf/{safe_stage}_result.json"


def stage_prompt_result_artifact(stage_id: str) -> str:
    safe_stage = stage_slug(stage_id) or "stage"
    return f".lgwf/{safe_stage}_prompt_result.json"


def stage_dir_from_path(path: str) -> str:
    parts = PurePosixPath(path).parts
    if len(parts) >= 2 and parts[0] == "wf":
        return parts[1]
    return ""


def stage_prompt_ref(stage_dir: str, all_files: list[str]) -> str:
    prompt_files: list[str] = []
    for candidate in all_files:
        parts = PurePosixPath(candidate).parts
        if len(parts) >= 4 and parts[0] == "wf" and parts[1] == stage_dir and parts[2] == "agents" and candidate.endswith(".md"):
            prompt_files.append("/".join(parts[2:]))
    return sorted(prompt_files)[0] if prompt_files else ""


def stage_contract_io(stage_id: str, stage: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    stage = stage or {}
    reads = workspace_artifacts_from_values(stage.get("input_sources"))
    writes = dedupe(
        [
            *workspace_artifacts_from_values(stage.get("outputs")),
            stage_runtime_artifact(stage_id),
        ]
    )
    return reads, writes


def contract_lines(reads: list[str], writes: list[str], indent: str = "    ") -> list[str]:
    lines: list[str] = []
    for artifact in reads:
        lines.append(f'{indent}READ workspace file "{artifact}";')
    for artifact in writes:
        lines.append(f'{indent}WRITE workspace file "{artifact}";')
    return lines or [f'{indent}WRITE workspace file ".lgwf/placeholder_result.json";']


def root_workflow_exact_content(
    workflow_name: str,
    stage_contracts: list[dict[str, Any]],
    business_stages: dict[str, dict[str, Any]],
) -> str:
    workflow_id = safe_lgwf_identifier(workflow_name, "generated_workflow")
    step_blocks: list[str] = []
    flow_nodes: list[str] = []
    for item in stage_contracts:
        stage_id = text(item.get("stage_id"))
        workflow_ref = safe_path(text(item.get("workflow_ref")))
        if not stage_id or not workflow_ref:
            continue
        parts = PurePosixPath(workflow_ref).parts
        stage_dir = parts[1] if len(parts) >= 3 and parts[0] == "wf" else stage_id
        child_ref = f"{stage_dir}/workflow.lgwf"
        node_id = f"stage_{safe_lgwf_identifier(stage_dir, stage_id)}"
        reads, writes = stage_contract_io(stage_id, business_stages.get(stage_id))
        step_blocks.append(
            "\n".join(
                [
                    f"STEP {node_id}",
                    f'  WORKFLOW "{child_ref}"',
                    "  CONTRACT {",
                    *contract_lines(reads, writes, indent="    "),
                    "  };",
                ]
            )
        )
        flow_nodes.append(node_id)
    if not flow_nodes:
        flow_nodes = ["noop"]
        step_blocks.append(
            "\n".join(
                [
                    "PY noop",
                    '  SCRIPT "scripts/run.py"',
                    "  CONTRACT {",
                    '    WRITE workspace file ".lgwf/noop_result.json";',
                    "  };",
                ]
            )
        )
    flow = "\n  THEN ".join(flow_nodes)
    return (
        f"WORKFLOW {workflow_id};\n"
        f"ENTRY {flow_nodes[0]};\n\n"
        "DEFAULTS {\n"
        '  ref_root workflow ".";\n'
        "  timeout_seconds 300;\n"
        "}\n\n"
        + "\n\n".join(step_blocks)
        + f"\n\nFLOW {flow};\n"
    )


def stage_workflow_exact_content(path: str, stage_id: str, stage: dict[str, Any] | None, prompt_ref: str = "") -> str:
    stage_dir = PurePosixPath(path).parts[1] if len(PurePosixPath(path).parts) >= 3 else stage_id
    workflow_id = safe_lgwf_identifier(f"stage_{stage_dir}", "stage_workflow")
    reads, writes = stage_contract_io(stage_id, stage)
    if prompt_ref:
        prompt_result = stage_prompt_result_artifact(stage_id)
        context_lines = [f'  CONTEXT workspace file "{artifact}"' for artifact in reads]
        prompt_contract = contract_lines(reads, [prompt_result], indent="    ")
        script_contract = contract_lines(dedupe([*reads, prompt_result]), writes, indent="    ")
        return (
            f"WORKFLOW {workflow_id};\n"
            "ENTRY run_agent;\n\n"
            "DEFAULTS {\n"
            '  ref_root workflow ".";\n'
            "  timeout_seconds 300;\n"
            "}\n\n"
            "CODEX run_agent\n"
            f'  PROMPT "{prompt_ref}"\n'
            + ("\n".join(context_lines) + "\n" if context_lines else "")
            + f'  OUTPUT_JSON "{prompt_result}" AS_FILE\n'
            "  TIMEOUT 300\n"
            "  CONTRACT {\n"
            + "\n".join(prompt_contract)
            + "\n  };\n\n"
            "PY run_stage\n"
            '  SCRIPT "scripts/run.py"\n'
            "  TIMEOUT 300\n"
            "  CONTRACT {\n"
            + "\n".join(script_contract)
            + "\n  };\n\n"
            "FLOW run_agent\n"
            "  THEN run_stage;\n"
        )
    return (
        f"WORKFLOW {workflow_id};\n"
        "ENTRY run_stage;\n\n"
        "DEFAULTS {\n"
        '  ref_root workflow ".";\n'
        "  timeout_seconds 300;\n"
        "}\n\n"
        "PY run_stage\n"
        '  SCRIPT "scripts/run.py"\n'
        "  TIMEOUT 300\n"
        "  CONTRACT {\n"
        + "\n".join(contract_lines(reads, writes, indent="    "))
        + "\n  };\n\n"
        "FLOW run_stage;\n"
    )


def prompt_exact_content(path: str, stage_id: str, stage: dict[str, Any] | None, business_goal: str) -> str:
    stage = stage or {}
    objective = text(stage.get("objective")) or f"完成 {stage_id} 阶段任务。"
    return (
        f"# {stage_id} agent prompt\n\n"
        "## Role\n"
        f"你负责执行 `{stage_id}` 阶段：{objective}\n\n"
        "## Inputs\n"
        "- 只读取当前 workflow 节点通过 CONTRACT 声明的 workspace artifact。\n"
        "- 不读取目标 package 之外的源码或历史运行记录。\n\n"
        "## Task\n"
        f"- 围绕目标 `{business_goal}` 生成本阶段约定输出。\n"
        "- 输出必须符合当前阶段 workflow 和 artifact contract。\n\n"
        "## Output\n"
        "- 按当前节点声明写入 workspace artifact。\n"
        "- 无法判断时输出结构化 blocked_reason，不扩大读取范围。\n\n"
        "## Boundaries\n"
        "- 不修改上游已确认需求、业务流或步骤设计。\n"
        "- 不写入未在 CONTRACT 中声明的文件。\n"
    )


def script_contract(path: str, stage_id: str, stage: dict[str, Any] | None, extra_input_files: list[str] | None = None) -> dict[str, Any]:
    reads, writes = stage_contract_io(stage_id, stage)
    reads = dedupe([*reads, *(extra_input_files or [])])
    if not reads:
        reads = ["无 workspace artifact 输入；从入口参数或空 object 初始化"]
    if not writes:
        writes = ["由调用 workflow CONTRACT 或入口参数决定"]
    return {
        "entrypoint": "main()",
        "runtime": "Python 3，标准库优先，UTF-8 no BOM。",
        "input_files": reads,
        "output_files": writes,
        "required_functions": [
            "load_json(path: Path) -> dict[str, Any]",
            "write_json(path: Path, payload: Any) -> None",
            "run(work_dir: Path) -> dict[str, Any]",
            "main() -> None",
        ],
        "behavior": [
            "从 Path.cwd() 定位 work dir。",
            "只读取 input_files 中声明的 workspace artifact；缺失可选输入时使用空 object 或明确失败。",
            "生成 output_files 中声明的 JSON 或 Markdown artifact，并返回结构化摘要。",
        ],
        "output_schema": {
            "type": "object",
            "required": ["status", "stage_id", "outputs"],
            "properties": {
                "status": {"enum": ["ok", "failed"]},
                "stage_id": {"type": "string"},
                "outputs": {"type": "array", "items": {"type": "string"}},
                "errors": {"type": "array", "items": {"type": "string"}},
            },
        },
        "error_handling": [
            "JSON 解析失败、路径越界或必填输入缺失时返回 status=failed，并把错误写入 errors。",
            "不得吞掉异常后生成不完整成功结果。",
        ],
        "validation": [
            f"`{path}` 可直接用 Python 运行或由 LGWF PY 节点调用。",
            "写出的 JSON 必须可解析，文本必须为 UTF-8 no BOM。",
        ],
    }


def test_contract(path: str, package_profile: str) -> dict[str, Any]:
    return {
        "test_framework": "Python unittest；可由仓库现有 test runner 或 python -m unittest 执行。",
        "scope": [
            "验证关键 package 文件、stage workflow 和 artifact contract 是否存在。",
            "验证路径边界：不得依赖本机绝对路径、盘符路径或目标 package 外部文件。",
            "覆盖最小 DSL 结构：WORKFLOW、ENTRY、CONTRACT、FLOW 和必要的 STEP/PY/CODEX 引用。",
        ],
        "fixtures": [
            "使用 tempfile 或测试夹具生成隔离 package。",
            "测试数据保持 UTF-8 no BOM，不读取 ws/.lgwf 运行历史作为源码输入。",
        ],
        "acceptance": [
            f"`{path}` 必须能在目标 package 根目录下独立运行。",
            "失败信息必须指向具体缺失文件、非法路径或 DSL 结构问题。",
            f"package_profile={package_profile} 的根文件和 stage 私有目录规则必须被覆盖。",
        ],
    }


def markdown_contract(path: str, package_profile: str) -> dict[str, Any]:
    sections = ["模块定位", "入口", "输入", "输出", "状态边界", "产物", "验证", "禁止事项"]
    if path == "SKILL.md":
        sections = ["技能定位", "触发方式", "入口 workflow", "输入契约", "输出产物", "边界"]
    if path.startswith("tests/"):
        sections = ["测试范围", "运行方式", "覆盖项", "不覆盖项"]
    return {
        "sections": sections,
        "language": "中文优先，代码标识符和路径保留英文。",
        "must_mention": [
            "target package 与 ws/.lgwf 运行状态分离。",
            f"package_profile={package_profile}",
        ],
        "forbidden": ["不得引用本机绝对路径。", "不得把运行态 .lgwf 写入目标 package。"],
    }


def root_artifact_json_contract(stage_contracts: list[dict[str, Any]], business_stages: dict[str, dict[str, Any]]) -> dict[str, Any]:
    all_reads: list[str] = []
    all_writes: list[str] = []
    for item in stage_contracts:
        stage_id = text(item.get("stage_id"))
        if not stage_id:
            continue
        reads, writes = stage_contract_io(stage_id, business_stages.get(stage_id))
        all_reads.extend(reads)
        all_writes.extend(writes)
    reads = dedupe(all_reads)
    writes = dedupe(all_writes)
    produced = set(writes)
    consumed = set(reads)
    bootstrap_inputs = [artifact for artifact in reads if artifact not in produced]
    final_outputs = [artifact for artifact in writes if artifact not in consumed] or writes
    return {
        "top_level_fields": [
            "bootstrap_inputs",
            "final_outputs",
            "script_writes",
            "runtime_records",
            "delivery_artifacts",
            "pending_confirmations",
        ],
        "required": ["bootstrap_inputs", "final_outputs", "script_writes"],
        "producer": "implementation stage",
        "consumer": "lgwf.py audit 和根 workflow 编排",
        "bootstrap_inputs": bootstrap_inputs,
        "final_outputs": final_outputs,
        "script_writes": writes,
        "runtime_records": [".lgwf/"],
    }


def json_contract(
    path: str,
    stage_id: str,
    stage: dict[str, Any] | None,
    stage_contracts: list[dict[str, Any]],
    business_stages: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if path == "entry_contract.json":
        return {
            "top_level_fields": ["input_schema", "output_schema", "state_boundary", "validation"],
            "required": ["input_schema", "output_schema"],
            "producer": "implementation stage",
            "consumer": "skill/workflow caller",
        }
    if path == "wf/artifact_contracts.json":
        return root_artifact_json_contract(stage_contracts, business_stages)
    if path.endswith("artifact_contracts.json"):
        reads, writes = stage_contract_io(stage_id, stage)
        return {
            "top_level_fields": ["bootstrap_inputs", "final_outputs", "script_writes", "runtime_records"],
            "required": ["bootstrap_inputs", "final_outputs"],
            "producer": "implementation stage",
            "consumer": "lgwf.py audit",
            "bootstrap_inputs": reads,
            "final_outputs": writes,
        }
    return {
        "top_level_fields": ["status", "data", "errors"],
        "required": ["status"],
        "producer": "对应实现脚本",
        "consumer": "下游 workflow 节点或测试",
    }


def file_content_contract(
    path: str,
    kind: str,
    owner: str,
    workflow_name: str,
    business_goal: str,
    package_profile: str,
    stage_contracts: list[dict[str, Any]],
    business_stages: dict[str, dict[str, Any]],
    all_files: list[str],
) -> dict[str, Any]:
    stage = business_stages.get(owner)
    stage_dir = stage_dir_from_path(path)
    prompt_ref = stage_prompt_ref(stage_dir, all_files) if stage_dir else ""
    if path == "wf/workflow.lgwf":
        return {
            "content_mode": "exact",
            "exact_content": root_workflow_exact_content(workflow_name, stage_contracts, business_stages),
        }
    if kind == "lgwf_workflow":
        return {
            "content_mode": "exact",
            "exact_content": stage_workflow_exact_content(path, owner, stage, prompt_ref),
        }
    if kind == "prompt":
        return {
            "content_mode": "exact",
            "exact_content": prompt_exact_content(path, owner, stage, business_goal),
        }
    if kind == "python_script":
        extra_inputs = [stage_prompt_result_artifact(owner)] if prompt_ref and "/scripts/" in path else []
        return {
            "content_mode": "contract",
            "script_contract": script_contract(path, owner, stage, extra_inputs),
        }
    if kind == "test":
        return {
            "content_mode": "contract",
            "test_contract": test_contract(path, package_profile),
        }
    if kind == "markdown_doc":
        return {
            "content_mode": "contract",
            "markdown_contract": markdown_contract(path, package_profile),
        }
    if kind == "json_contract":
        return {
            "content_mode": "contract",
            "json_contract": json_contract(path, owner, stage, stage_contracts, business_stages),
        }
    return {"content_mode": "contract"}


def file_design(
    path: str,
    owner: str,
    business_goal: str,
    workflow_name: str,
    package_profile: str,
    stage_contracts: list[dict[str, Any]],
    business_stages: dict[str, dict[str, Any]],
    all_files: list[str],
) -> dict[str, Any]:
    kind = file_kind(path)
    design = {
        "path": path,
        "kind": kind,
        "owner_step": owner,
        "purpose": f"定义 `{path}` 的职责、结构和验收边界，服务目标：{business_goal}",
        "required_structure": file_required_structure(path, kind),
        "reads": ["实现阶段读取已确认 requirements、business_flow、scaffold plan 和 step_designs。"],
        "writes": [f"实现阶段写入 `{path}`。"],
        "dependencies": ["依赖动态 step design contract、schema 和已确认 scaffold plan。"],
        "acceptance_notes": file_acceptance_notes(path, kind),
        "forbidden": [
            "不得包含完整源码字段。",
            "不得使用绝对路径、盘符路径或 `..`。",
            "不得写入目标 package 外部。",
        ],
        "source_refs": ["create_requirements.json", "business_flow.json", "scaffold_package_result.json"],
    }
    design.update(
        file_content_contract(
            path,
            kind,
            owner,
            workflow_name,
            business_goal,
            package_profile,
            stage_contracts,
            business_stages,
            all_files,
        )
    )
    return design


def directory_design(path: str, files: list[str], owner: str) -> dict[str, Any]:
    expected = [candidate for candidate in files if candidate == path or candidate.startswith(f"{path}/")]
    if path == ".":
        expected = [candidate for candidate in files if "/" not in candidate]
    return {
        "path": path,
        "purpose": f"承载 `{path}` 目录下的目标文件，并保持源码目录与 ws/.lgwf 运行状态分离。",
        "owner_step": owner,
        "expected_files": expected[:12] or [f"{path}/README.md" if path != "." else "README.md"],
        "forbidden": ["不得承载运行态 .lgwf 状态。", "不得写入目标 package 外部。"],
        "source_refs": ["scaffold_package_result.scaffold_plan.create_dirs"],
    }


def build_stage_lookup(stages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for stage in stages:
        stage_id = text(stage.get("stage_id"))
        if stage_id:
            result[stage_id] = stage
    return result


def build_step(
    *,
    step_slug_value: str,
    step_name: str,
    stage_id: str,
    goal: str,
    target_files: list[str],
    target_dirs: list[str],
    runtime_artifacts: list[str],
    stage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stage = stage or {}
    inputs = string_list(stage.get("input_sources")) or ["已确认 requirements", "已确认 business_flow", "scaffold plan"]
    outputs = string_list(stage.get("outputs")) or target_files
    dependencies = string_list(stage.get("depends_on")) or ["动态 step design contract"]
    return {
        "step_slug": step_slug_value,
        "step_name": step_name,
        "stage_id": stage_id,
        "goal": goal,
        "inputs": inputs,
        "outputs": outputs,
        "dependencies": dependencies,
        "implementation_suggestions": [
            "按 file_designs 和 directory_designs 生成目标文件，不输出完整源码到步骤设计。",
            "保持根 workflow 薄编排，业务逻辑下沉到阶段 scripts、共享 runtime 或直接脚本入口。",
            "所有路径使用 package-relative 安全路径。",
        ],
        "acceptance_notes": [
            "target_files 中每个路径必须有对应 file_design。",
            "target_dirs 中每个路径必须有对应 directory_design。",
            "运行状态只允许通过 runtime_artifacts 指向 .lgwf 或 reports。",
        ],
        "out_of_scope": list(OUT_OF_SCOPE),
        "confirmation_points": [
            "确认本 step 的输入、输出、目标文件和目标目录是否覆盖当前阶段职责。",
        ],
        "target_files": dedupe(target_files),
        "target_dirs": dedupe(target_dirs),
        "runtime_artifacts": dedupe(runtime_artifacts),
        "source_refs": ["step_design_validation_contract", "business_flow.stages", "scaffold_plan"],
        "risk_notes": [
            "不得从 scaffold plan 之外额外发明 workflow 目录。",
            "阶段 workflow 必须来自 required_stage_workflows。",
        ],
    }


def ensure_schema_top_level(schema: dict[str, Any], proposal: dict[str, Any]) -> None:
    for field in string_list(schema.get("required")):
        if field not in proposal:
            raise ValueError(f"deterministic step design proposal missing top-level field: {field}")


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    workflow_root = Path(__file__).resolve().parents[1]
    requirements = load_json_object(lgwf_dir / "create_requirements.json")
    business_flow = load_json_object(lgwf_dir / "business_flow.json")
    scaffold = load_json_object(lgwf_dir / "scaffold_package_result.json")
    contract = load_json_object(lgwf_dir / "step_design_validation_contract.json")
    schema = load_json_object(workflow_root / "resources" / "step_designs_proposal.schema.json")
    _passing_example = load_json_object(workflow_root / "resources" / "step_designs_passing_example.json")

    confirmed_requirements = nested_dict(requirements, "confirmed") or requirements
    confirmed_business_flow = nested_dict(business_flow, "confirmed") or business_flow
    scaffold_plan = nested_dict(scaffold, "scaffold_plan") or scaffold
    identity = nested_dict(contract, "identity")
    stage_contracts = dict_list(contract.get("required_stage_workflows"))
    business_stages = build_stage_lookup(dict_list(confirmed_business_flow.get("stages")))

    workflow_id = text(identity.get("workflow_id")) or text(confirmed_requirements.get("workflow_id")) or text(scaffold_plan.get("workflow_name"))
    workflow_name = text(identity.get("workflow_name")) or text(confirmed_requirements.get("workflow_name")) or workflow_id
    target_root = text(identity.get("target_package_root")) or text(confirmed_requirements.get("target_package_root")) or text(scaffold_plan.get("target_package_root"))
    package_profile = text(identity.get("package_profile")) or text(scaffold_plan.get("package_profile")) or "lgwf_workflow_package"
    business_goal = text(confirmed_business_flow.get("business_goal")) or text(confirmed_requirements.get("purpose")) or workflow_name

    create_files = dedupe([safe_path(path) for path in string_list(scaffold_plan.get("create_files"))])
    required_files = dedupe([safe_path(path) for path in string_list(contract.get("required_file_designs"))])
    all_files = dedupe([*create_files, *required_files])
    create_dirs = dedupe([safe_path(path) for path in string_list(scaffold_plan.get("create_dirs"))])

    stage_by_dir: dict[str, str] = {}
    stage_dirs: dict[str, str] = {}
    for item in stage_contracts:
        stage_id = text(item.get("stage_id"))
        workflow_ref = safe_path(text(item.get("workflow_ref")))
        if not stage_id or not workflow_ref:
            continue
        stage_dir = stage_dir_from_workflow_ref(workflow_ref, stage_id)
        stage_by_dir[stage_dir] = stage_id
        stage_dirs[stage_id] = stage_dir

    file_designs = [
        file_design(
            path,
            file_owner(path, stage_by_dir),
            business_goal,
            workflow_name,
            package_profile,
            stage_contracts,
            business_stages,
            all_files,
        )
        for path in all_files
    ]
    file_design_paths = {item["path"] for item in file_designs}

    root_files = [
        path
        for path in all_files
        if path in ROOT_CONTRACT_FILES
        or path.startswith("scripts/")
        or path.startswith("tests/")
        or path.startswith("wf/shared/")
    ]
    root_dirs = dedupe(
        [
            "wf",
            *[directory for path in root_files for directory in parent_dirs(path)],
            *[path for path in create_dirs if path in ("scripts", "tests", "ws", "wf", "wf/shared/scripts")],
        ]
    )
    steps: list[dict[str, Any]] = [
        build_step(
            step_slug_value="package_contracts",
            step_name="生成模块入口契约与根编排",
            stage_id=text(stage_contracts[0].get("stage_id")) if stage_contracts else "package_contracts",
            goal="建立目标 package 的入口文档、入口契约、根 workflow、artifact contract、共享脚本和最小测试设计。",
            target_files=root_files,
            target_dirs=root_dirs,
            runtime_artifacts=[".lgwf/implementation_context.json", ".lgwf/implementation_units.json"],
        )
    ]

    for item in stage_contracts:
        stage_id = text(item.get("stage_id"))
        workflow_ref = safe_path(text(item.get("workflow_ref")))
        if not stage_id or not workflow_ref:
            continue
        stage_dir = stage_dirs[stage_id]
        stage_files = [path for path in all_files if path == workflow_ref or path.startswith(f"wf/{stage_dir}/")]
        if workflow_ref not in stage_files:
            stage_files.insert(0, workflow_ref)
        stage_target_dirs = dedupe(
            [
                f"wf/{stage_dir}",
                *[directory for path in stage_files for directory in parent_dirs(path) if directory.startswith(f"wf/{stage_dir}")],
                *[path for path in create_dirs if path == f"wf/{stage_dir}" or path.startswith(f"wf/{stage_dir}/")],
            ]
        )
        stage = business_stages.get(stage_id)
        steps.append(
            build_step(
                step_slug_value=stage_slug(stage_id),
                step_name=f"设计 {stage_id} 阶段",
                stage_id=stage_id,
                goal=text(stage.get("objective")) if stage else f"设计 `{stage_id}` 阶段 workflow、prompt、脚本和资源边界。",
                target_files=stage_files,
                target_dirs=stage_target_dirs,
                runtime_artifacts=[f".lgwf/{stage_id}_result.json"],
                stage=stage,
            )
        )

    referenced_dirs = dedupe([path for step in steps for path in step["target_dirs"]])
    directory_designs = [
        directory_design(path, sorted(file_design_paths), file_owner(f"{path}/workflow.lgwf", stage_by_dir))
        for path in referenced_dirs
        if path
    ]

    proposal = {
        "workflow_id": workflow_id,
        "workflow_name": workflow_name,
        "target_package_root": target_root,
        "package_profile": package_profile,
        "source_business_flow_stages": [text(item.get("stage_id")) for item in stage_contracts if text(item.get("stage_id"))]
        or [steps[0]["stage_id"]],
        "directory_designs": directory_designs,
        "file_designs": file_designs,
        "step_designs": steps,
        "design_rationale": [
            "首轮步骤设计由确定性脚本根据已确认 requirements、business_flow、scaffold plan、schema 和动态 step design contract 生成，避免 Codex 首轮设计读取过宽上下文。",
            "动态 contract 的 required_stage_workflows 是唯一允许生成的阶段 workflow 清单；stage_aliases 仅用于阶段 id 归一化。",
            "所有 scaffold create_files 都进入 file_designs 并被 step_designs.target_files 引用，保证 04 implementation units 不再从 scaffold 隐式补齐。",
        ],
    }
    ensure_schema_top_level(schema, proposal)
    write_json(lgwf_dir / "step_designs_proposal.json", proposal)
    print(
        json.dumps(
            {
                "lgwf_wf_create.step_design_generate_result": {
                    "generated_by": "deterministic_python",
                    "proposal_file": ".lgwf/step_designs_proposal.json",
                    "file_design_count": len(file_designs),
                    "directory_design_count": len(directory_designs),
                    "step_design_count": len(steps),
                }
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
