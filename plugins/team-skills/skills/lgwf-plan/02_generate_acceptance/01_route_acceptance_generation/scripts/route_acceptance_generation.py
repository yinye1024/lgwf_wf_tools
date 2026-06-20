from __future__ import annotations

import json
from pathlib import Path


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def format_confirmation(plan: dict, acceptance: dict) -> dict:
    plan_tasks = {task.get("task_id"): task for task in plan.get("tasks", []) if isinstance(task, dict)}
    rows = []
    for item in acceptance.get("tasks", []):
        if not isinstance(item, dict):
            continue
        task_id = item.get("task_id")
        rows.append({"task_id": task_id, "plan": plan_tasks.get(task_id, {}), "acceptance": item})
    return {"tasks": rows, "instruction": "approve or reject the aligned plan and acceptance contract"}


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

