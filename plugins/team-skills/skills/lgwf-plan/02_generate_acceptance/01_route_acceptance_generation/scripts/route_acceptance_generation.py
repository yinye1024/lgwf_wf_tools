from __future__ import annotations

import json
from pathlib import Path


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def as_list(value) -> list:
    return value if isinstance(value, list) else []


def derive_summary(plan: dict, acceptance: dict) -> dict:
    summary = plan.get("summary")
    if isinstance(summary, dict):
        return summary

    tasks = [task for task in plan.get("tasks", []) if isinstance(task, dict)]
    task_titles = [task.get("title") or task.get("task_id") for task in tasks if task.get("title") or task.get("task_id")]
    acceptance_tasks = [task for task in acceptance.get("tasks", []) if isinstance(task, dict)]
    checks = []
    for task in acceptance_tasks:
        checks.extend(as_list(task.get("required_checks"))[:2])

    return {
        "problem_statement": "将用户目标拆成可执行、可验收的工作契约，供后续实现阶段按 task 推进。",
        "proposed_approach": "按依赖顺序拆分任务：先稳定前置契约，再生成结构和设计文档，最后按已确认设计实现初稿。",
        "workflow_flow": task_titles,
        "key_decisions": [
            {
                "decision": "先确认契约，再创建框架，最后实现",
                "reason": "后续步骤依赖前置需求、业务流转和步骤设计，先固化契约可以降低返工。",
                "tradeoff": "确认节点增加，但每个阶段的输入输出更清晰。",
            }
        ],
        "alternatives_considered": [],
        "open_questions": [],
        "quality_bar": checks[:5],
    }


def format_confirmation(plan: dict, acceptance: dict) -> dict:
    plan_tasks = {task.get("task_id"): task for task in plan.get("tasks", []) if isinstance(task, dict)}
    rows = []
    for item in acceptance.get("tasks", []):
        if not isinstance(item, dict):
            continue
        task_id = item.get("task_id")
        rows.append({"task_id": task_id, "plan": plan_tasks.get(task_id, {}), "acceptance": item})
    return {
        "summary": derive_summary(plan, acceptance),
        "tasks": rows,
        "instruction": "approve or reject the aligned plan and acceptance contract",
    }


def main() -> None:
    root = Path.cwd()
    plan = load(root / ".lgwf" / "react_task_plan_proposal.json")
    acceptance = load(root / ".lgwf" / "react_acceptance_proposal.json")
    observe = load(root / ".lgwf" / "react_acceptance_observe.json")
    ok = observe.get("verdict") == "pass" and observe.get("ready_for_confirmation") is True
    direction = {
        "status": "ready_for_confirmation" if ok else "acceptance_generation_failed",
        "allowed_directions": ["retry_acceptance_generation", "stop"] if not ok else [],
        "issues": observe.get("issues", []),
        "required_changes": observe.get("required_changes", []),
    }
    confirmation = format_confirmation(plan, acceptance) if ok else direction
    (root / ".lgwf").mkdir(parents=True, exist_ok=True)
    (root / ".lgwf" / "react_acceptance_generation_direction.json").write_text(
        json.dumps(direction, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"lgwf_plan.acceptance_generation_direction": direction, "lgwf_plan.confirmation_context": confirmation}, ensure_ascii=False))


if __name__ == "__main__":
    main()

