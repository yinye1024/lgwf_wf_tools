"""确定性生成步骤设计草案。

这个脚本替代原先的 Codex 步骤设计节点，避免在创建 workflow 时因为
LLM 子进程无输出而卡住。它只消费已确认业务流和脚手架计划，仍然把结果
交给 `confirm_step_designs` 人工确认。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STEP_OUTPUTS = [
    "目标阶段的 workflow、script、prompt 或 resource 设计约束",
    "可被 implement_steps_react 消费的文件和目录说明",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def confirmed_payload(data: dict[str, Any]) -> dict[str, Any]:
    confirmed = data.get("confirmed")
    return confirmed if isinstance(confirmed, dict) else data


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def kebab(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or fallback


def stage_id(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    return cleaned or fallback


def load_business_flow(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    confirmed = confirmed_payload(load_json(lgwf_dir / "business_flow.json"))
    if confirmed:
        return confirmed
    return confirmed_payload(load_json(lgwf_dir / "business_flow_proposal.json"))


def load_requirements(root: Path) -> dict[str, Any]:
    return confirmed_payload(load_json(root / ".lgwf" / "create_requirements.json"))


def load_scaffold_plan(root: Path) -> dict[str, Any]:
    payload = load_json(root / ".lgwf" / "scaffold_package_result.json")
    nested = payload.get("lgwf_wf_create.scaffold_package_result")
    if isinstance(nested, dict):
        payload = nested
    plan = payload.get("scaffold_plan")
    return plan if isinstance(plan, dict) else payload


def stage_summary(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, item in enumerate(stages, start=1):
        sid = stage_id(str(item.get("stage_id", "")), f"stage_{index:02d}")
        result.append(
            {
                "stage_id": sid,
                "stage_name": str(item.get("stage_name") or item.get("name") or sid),
                "objective": str(item.get("objective") or item.get("goal") or ""),
                "key_nodes": as_string_list(item.get("key_nodes")),
                "human_approval": bool(item.get("human_approval", False)),
                "outputs": as_string_list(item.get("outputs")),
            }
        )
    return result


def fallback_downstream_inputs(stages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, item in enumerate(stages, start=1):
        sid = stage_id(str(item.get("stage_id", "")), f"stage_{index:02d}")
        result.append(
            {
                "step_slug": kebab(sid, f"step-{index:02d}"),
                "stage_id": sid,
                "consumes": [
                    ".lgwf/business_flow.json",
                    ".lgwf/scaffold_package_result.json",
                ],
                "expected_artifacts": as_string_list(item.get("outputs")) or DEFAULT_STEP_OUTPUTS,
            }
        )
    return result


def build_step_inputs(business_flow: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = as_dict_list(business_flow.get("downstream_step_inputs"))
    stages = stage_summary(as_dict_list(business_flow.get("stages")))
    if not raw_items:
        return fallback_downstream_inputs(stages)

    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items, start=1):
        paired_stage = stages[index - 1] if index <= len(stages) else {}
        sid = stage_id(
            str(item.get("stage_id") or paired_stage.get("stage_id") or ""),
            f"stage_{index:02d}",
        )
        slug = kebab(str(item.get("step_slug") or sid), f"step-{index:02d}")
        result.append(
            {
                "step_slug": slug,
                "stage_id": sid,
                "stage_name": str(paired_stage.get("stage_name") or sid),
                "consumes": as_string_list(item.get("consumes")),
                "expected_artifacts": as_string_list(item.get("expected_artifacts")) or DEFAULT_STEP_OUTPUTS,
            }
        )
    return result


def bullet_lines(items: list[str], empty: str = "无") -> list[str]:
    if not items:
        return [f"- {empty}"]
    return [f"- {item}" for item in items]


def render_step_doc(
    *,
    step: dict[str, Any],
    business_flow: dict[str, Any],
    scaffold_plan: dict[str, Any],
    dependencies: list[dict[str, Any]],
) -> list[str]:
    slug = str(step["step_slug"])
    sid = str(step["stage_id"])
    target_root = str(
        scaffold_plan.get("target_package_root")
        or business_flow.get("target_package_root")
        or "target-package"
    )
    workflow_name = str(
        scaffold_plan.get("workflow_name")
        or business_flow.get("workflow_name")
        or "unnamed-workflow"
    )
    stage_deps = [
        f"{item.get('from_stage')} -> {item.get('to_stage')}：{item.get('handoff')}"
        for item in dependencies
        if item.get("to_stage") == sid or item.get("from_stage") == sid
    ]
    return [
        f"# {slug}",
        "",
        "## step_slug",
        "",
        f"`{slug}`",
        "",
        "## step_name",
        "",
        str(step.get("stage_name") or slug),
        "",
        "## goal",
        "",
        f"为 `{workflow_name}` 的 `{sid}` 阶段定义可实现、可审阅的 workflow 步骤设计，确保后续实现只在 `{target_root}` 内生成 package 文件，并保持 `ws/.lgwf` 作为唯一运行状态边界。",
        "",
        "## inputs",
        "",
        "- 上游阶段或节点：",
        f"  - `{sid}` 来源于已确认业务流。",
        "- 依赖文件或状态：",
        *[f"  - `{item}`" for item in (step.get("consumes") or [".lgwf/business_flow.json", ".lgwf/scaffold_package_result.json"])],
        "- 关键约束：",
        "  - 遵守 `wf/` 唯一 workflow root。",
        "  - 阶段目录必须是第一层 `wf/<stage>/`，不得创建孙级 workflow。",
        "  - 运行状态只能写入 `ws/.lgwf`。",
        "",
        "## outputs",
        "",
        *bullet_lines([str(item) for item in step.get("expected_artifacts", [])]),
        "",
        "## dependencies",
        "",
        *bullet_lines(stage_deps, "无额外阶段依赖；按业务流顺序执行。"),
        "",
        "## implementation_suggestions",
        "",
        f"- 在目标 package 内为 `{sid}` 准备 `wf/{sid}/workflow.lgwf`。",
        f"- 若该阶段需要 prompt、脚本或资源，分别放入 `wf/{sid}/agents/`、`wf/{sid}/scripts/`、`wf/{sid}/resources/`。",
        "- 根 `wf/workflow.lgwf` 只编排第一层子 workflow，不承载阶段内部细节。",
        "- 复用现有脚本能力时，先用 wrapper 固化输入输出契约，不把运行态文件写入源码根目录。",
        "",
        "## acceptance_notes",
        "",
        "- 人工确认时重点核对 step_slug、stage_id、输出文件和只读/写入边界是否与已确认业务流一致。",
        "- 如果 `target_dir` 位于只读位置，输出目录策略必须在实现脚本中显式失败或回退，并写入摘要。",
        "- 如果 `max_files` 或 `depth` 导致扫描截断，摘要和报告必须记录截断事实。",
        "",
        "## out_of_scope",
        "",
        "- `lgwf-wf-prompt-fix` 集成",
        "- `lgwf-wf-tools` registry 自动注册",
        "- 自动修复、自动发布或端到端运行保证",
    ]


def build_step_designs(root: Path) -> dict[str, Any]:
    business_flow = load_business_flow(root)
    if not business_flow:
        raise RuntimeError("缺少 .lgwf/business_flow.json 或 .lgwf/business_flow_proposal.json")
    requirements = load_requirements(root)
    scaffold_plan = load_scaffold_plan(root)
    stages = stage_summary(as_dict_list(business_flow.get("stages")))
    dependencies = as_dict_list(business_flow.get("stage_dependencies"))
    steps = build_step_inputs(business_flow)

    docs_dir = root / "docs" / "steps"
    target_root = str(
        business_flow.get("target_package_root")
        or requirements.get("target_package_root")
        or scaffold_plan.get("target_package_root", "")
    ).strip()
    package_profile = str(requirements.get("package_profile") or scaffold_plan.get("package_profile", "")).strip()
    if package_profile == "internal_workflow_package":
        workspace_root = next((candidate for candidate in [root.resolve(), *root.resolve().parents] if (candidate / "skills").is_dir()), root.resolve())
        if target_root and (workspace_root / target_root / "SKILL.md").is_file():
            package_profile = "skill_wrapped_workflow"
    step_designs: list[dict[str, Any]] = []
    for step in steps:
        doc_path = f"docs/steps/{step['step_slug']}.md"
        write_markdown(
            root / doc_path,
            render_step_doc(
                step=step,
                business_flow=business_flow,
                scaffold_plan=scaffold_plan,
                dependencies=dependencies,
            ),
        )
        step_designs.append(
            {
                "step_slug": step["step_slug"],
                "step_name": step.get("stage_name") or step["step_slug"],
                "stage_id": step["stage_id"],
                "doc_path": doc_path,
                "confirmation_points": [
                    "确认步骤输入输出可被 implement_steps_react 消费",
                    "确认路径和状态边界未越过目标 package",
                    "确认该步骤仍是设计草案而非实现文件",
                ],
                "expected_artifacts": step.get("expected_artifacts", []),
            }
        )

    proposal = {
        "workflow_name": business_flow.get("workflow_name") or requirements.get("workflow_name") or scaffold_plan.get("workflow_name", ""),
        "target_package_root": target_root,
        "package_profile": package_profile,
        "generation_mode": "deterministic_python",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_business_flow_stages": stages,
        "stage_dependencies": dependencies,
        "step_designs": step_designs,
        "stage_directory_exemptions": {},
        "scaffold_plan_summary": {
            "package_profile": scaffold_plan.get("package_profile", ""),
            "target_package_root": scaffold_plan.get("target_package_root", ""),
            "create_dirs_count": len(scaffold_plan.get("create_dirs", [])) if isinstance(scaffold_plan.get("create_dirs"), list) else 0,
            "create_files_count": len(scaffold_plan.get("create_files", [])) if isinstance(scaffold_plan.get("create_files"), list) else 0,
        },
        "review_notes": [
            "步骤设计由确定性脚本生成，仍需 confirm_step_designs 人工确认。",
            "后续实现阶段必须复制这些步骤文档到目标 package 的 wf/docs/steps/。",
        ],
    }
    write_json(root / ".lgwf" / "step_designs_proposal.json", proposal)
    return {
        "status": "ok",
        "proposal_path": ".lgwf/step_designs_proposal.json",
        "docs_dir": str(docs_dir),
        "step_count": len(step_designs),
        "step_designs_proposal": proposal,
    }


def main() -> None:
    result = build_step_designs(Path.cwd())
    print(json.dumps({"lgwf_wf_create.step_design_result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
