from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_manager():
    path = Path(__file__).with_name("manage_react_task.py")
    spec = importlib.util.spec_from_file_location("manage_react_task", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def read(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing required artifact: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def main() -> None:
    root = Path.cwd()
    manager = load_manager()
    plan = read(root / ".lgwf" / "react_task_plan.json")
    acceptance = read(root / ".lgwf" / "react_acceptance_plan.json")
    task = manager.get_current_task(root)
    if task is None:
        context = {"all_done": True, "task": None}
    else:
        task_id = task.get("task_id")
        acceptance_map = {item.get("task_id"): item for item in acceptance.get("tasks", []) if isinstance(item, dict)}
        context = {
            "all_done": False,
            "task": task,
            "acceptance": acceptance_map.get(task_id, {}),
            "max_attempts": 3,
        }
        manager.update_status(root, task_id, "in_progress")
    path = root / ".lgwf" / "react_task_context.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"lgwf_plan.current_task_context": context}, ensure_ascii=False))


if __name__ == "__main__":
    main()

