from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TERMINAL_STATUSES = {"passed", "skipped"}


def _lgwf(root: Path) -> Path:
    return root / ".lgwf"


def _read(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _task_ids(plan: dict) -> list[str]:
    return [task["task_id"] for task in plan.get("tasks", []) if isinstance(task, dict) and task.get("task_id")]


def init_plan(root: str | Path, plan: dict) -> dict:
    root = Path(root)
    tasks = []
    for item in plan.get("tasks", []):
        task = dict(item)
        task["status"] = task.get("status") or "planned"
        task["attempts"] = int(task.get("attempts") or 0)
        tasks.append(task)
    stored = dict(plan)
    stored["tasks"] = tasks
    stored["current_task_id"] = get_next_pending_task(stored)
    _write(_lgwf(root) / "react_task_plan.json", stored)
    return stored


def set_acceptance(root: str | Path, acceptance: dict) -> dict:
    root = Path(root)
    plan = _read(_lgwf(root) / "react_task_plan.json", {})
    plan_ids = set(_task_ids(plan))
    acceptance_ids = set(_task_ids(acceptance))
    if plan_ids != acceptance_ids:
        raise ValueError(f"plan and acceptance task_id mismatch: plan={sorted(plan_ids)} acceptance={sorted(acceptance_ids)}")
    acceptance_by_id = {
        item.get("task_id"): item for item in acceptance.get("tasks", []) if isinstance(item, dict)
    }
    required = {"criteria", "required_checks", "review_focus", "out_of_scope", "plan_validation_map"}
    for task in plan.get("tasks", []):
        task_id = task.get("task_id")
        spec = acceptance_by_id.get(task_id) or {}
        missing = [key for key in sorted(required) if key not in spec or spec.get(key) in (None, [], "")]
        if missing:
            raise ValueError(f"acceptance for {task_id} missing required fields: {missing}")
        steps = task.get("implementation_steps") or []
        if steps:
            indexes = {
                item.get("plan_step_index")
                for item in spec.get("plan_validation_map", [])
                if isinstance(item, dict)
            }
            expected = set(range(len(steps)))
            if indexes != expected:
                raise ValueError(
                    f"acceptance for {task_id} must cover implementation_steps indexes {sorted(expected)}"
                )
    for task in plan.get("tasks", []):
        if task.get("status") == "planned":
            task["status"] = "acceptance_specified"
    _write(_lgwf(root) / "react_task_plan.json", plan)
    _write(_lgwf(root) / "react_acceptance_plan.json", acceptance)
    return acceptance


def get_next_pending_task(plan: dict) -> str | None:
    for task in plan.get("tasks", []):
        if task.get("status") not in TERMINAL_STATUSES:
            return task.get("task_id")
    return None


def get_current_task(root: str | Path) -> dict | None:
    root = Path(root)
    plan = _read(_lgwf(root) / "react_task_plan.json", {})
    current = plan.get("current_task_id") or get_next_pending_task(plan)
    for task in plan.get("tasks", []):
        if task.get("task_id") == current:
            return task
    return None


def update_status(root: str | Path, task_id: str, status: str) -> dict:
    root = Path(root)
    plan_path = _lgwf(root) / "react_task_plan.json"
    plan = _read(plan_path, {})
    for task in plan.get("tasks", []):
        if task.get("task_id") == task_id:
            task["status"] = status
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            break
    plan["current_task_id"] = get_next_pending_task(plan)
    _write(plan_path, plan)
    return plan


def append_history(root: str | Path, entry: dict) -> list:
    root = Path(root)
    path = _lgwf(root) / "react_task_history.json"
    history = _read(path, [])
    if not isinstance(history, list):
        history = []
    item = dict(entry)
    item.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
    history.append(item)
    _write(path, history)
    return history


def record_review(root: str | Path, task_id: str, result: dict, max_attempts: int = 3) -> dict:
    root = Path(root)
    plan_path = _lgwf(root) / "react_task_plan.json"
    plan = _read(plan_path, {})
    status = "needs_repair"
    route = "continue_repair"
    attempts = 0
    for task in plan.get("tasks", []):
        if task.get("task_id") != task_id:
            continue
        attempts = int(task.get("attempts") or 0) + 1
        task["attempts"] = attempts
        task["last_result"] = result
        if result.get("pass") is True or result.get("verdict") == "pass":
            status = "passed"
            route = "move_next_task"
        elif attempts >= max_attempts:
            status = "blocked_for_user"
            route = "requires_user_approval"
        task["status"] = status
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        break
    plan["current_task_id"] = get_next_pending_task(plan)
    if route == "move_next_task" and plan["current_task_id"] is None:
        route = "all_done"
    _write(plan_path, plan)
    append_history(root, {"task_id": task_id, "attempts": attempts, "status": status, "route": route, "result": result})
    route_data = {"task_id": task_id, "route": route, "status": status, "attempts": attempts}
    _write(_lgwf(root) / "react_task_route.json", route_data)
    return route_data
