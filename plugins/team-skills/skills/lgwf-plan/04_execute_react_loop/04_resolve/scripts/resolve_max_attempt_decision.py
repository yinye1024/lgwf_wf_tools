from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_action(value: Any) -> str:
    if isinstance(value, str):
        raw = value
    elif isinstance(value, dict):
        nested_value = value.get("value")
        if isinstance(nested_value, dict):
            nested_action = normalize_action(nested_value)
            if nested_action:
                return nested_action
        raw = str(
            value.get("action")
            or value.get("decision")
            or value.get("approval")
            or value.get("status")
            or ""
        )
    else:
        raw = ""
    action = raw.strip().lower().replace("-", "_")
    aliases = {
        "approve": "accept",
        "approved": "accept",
        "accept_current": "accept",
        "accepted": "accept",
        "repair": "continue",
        "retry": "continue",
        "adjust": "continue",
        "continue_repair": "continue",
        "skip_task": "skip",
        "skipped": "skip",
        "reject": "stop",
        "rejected": "stop",
        "abort": "stop",
        "cancel": "stop",
        "blocked": "stop",
    }
    return aliases.get(action, action)


def find_decision(lgwf_dir: Path) -> dict[str, Any]:
    for name in (
        "react_task_max_attempt_decision.json",
        "max_attempt_decision.json",
        "react_task_max_attempt_approval.json",
    ):
        data = load(lgwf_dir / name, None)
        if isinstance(data, dict):
            return data
    return {"action": "stop", "comment": "missing max-attempt decision artifact"}


def get_next_pending_task(plan: dict[str, Any]) -> str | None:
    for task in plan.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if task.get("status") in {
            None,
            "",
            "planned",
            "pending",
            "acceptance_specified",
            "needs_repair",
            "in_progress",
            "blocked_for_user",
        }:
            return task.get("task_id")
    return None


def resolve(plan: dict[str, Any], route: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    task_id = route.get("task_id") or plan.get("current_task_id")
    if not task_id:
        return {"route": "all_done", "task_id": None, "status": "all_done", "decision": decision}

    action = normalize_action(decision)
    if action not in {"continue", "accept", "skip", "stop"}:
        raise SystemExit("max-attempt decision action must be continue, accept, skip, or stop")

    now = datetime.now(timezone.utc).isoformat()
    status_by_action = {
        "continue": "needs_repair",
        "accept": "passed",
        "skip": "skipped",
        "stop": "stopped_by_user",
    }
    route_by_action = {
        "continue": "continue_repair",
        "accept": "move_next_task",
        "skip": "move_next_task",
        "stop": "all_done",
    }

    for task in plan.get("tasks", []):
        if not isinstance(task, dict) or task.get("task_id") != task_id:
            continue
        task["status"] = status_by_action[action]
        task["max_attempt_decision"] = decision
        task["updated_at"] = now
        if action == "continue":
            task["attempts"] = 0
        break

    if action == "continue":
        plan["current_task_id"] = task_id
    elif action == "stop":
        plan["current_task_id"] = None
    else:
        plan["current_task_id"] = get_next_pending_task(plan)

    next_route = route_by_action[action]
    if next_route == "move_next_task" and plan.get("current_task_id") is None:
        next_route = "all_done"
    return {"route": next_route, "task_id": task_id, "status": status_by_action[action], "decision": decision}


def append_history(lgwf_dir: Path, entry: dict[str, Any]) -> None:
    history = load(lgwf_dir / "react_task_history.json", [])
    if not isinstance(history, list):
        history = []
    item = dict(entry)
    item.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
    history.append(item)
    write(lgwf_dir / "react_task_history.json", history)


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    route = load(lgwf_dir / "react_task_route.json", {"route": "all_done"})
    if route.get("route") != "requires_user_approval":
        print(json.dumps({"lgwf_plan.react_task_route": route}, ensure_ascii=False))
        return

    plan = load(lgwf_dir / "react_task_plan.json", {})
    if not isinstance(plan, dict):
        raise SystemExit("react_task_plan.json must be a JSON object")
    decision = find_decision(lgwf_dir)
    resolved = resolve(plan, route, decision)
    write(lgwf_dir / "react_task_plan.json", plan)
    write(lgwf_dir / "react_task_route.json", resolved)
    append_history(lgwf_dir, {"task_id": resolved.get("task_id"), "status": resolved.get("status"), "route": resolved.get("route"), "decision": decision})
    print(json.dumps({"lgwf_plan.react_task_route": resolved, "lgwf_plan.max_attempt_resolution": resolved}, ensure_ascii=False))


if __name__ == "__main__":
    main()
