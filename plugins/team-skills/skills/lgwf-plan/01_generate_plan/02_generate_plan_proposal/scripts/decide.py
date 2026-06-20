from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def main() -> None:
    root = Path.cwd()
    proposal = load_json(root / ".lgwf" / "react_task_plan_proposal.json")
    observe = load_json(root / ".lgwf" / "react_task_plan_observe.json")
    tasks = proposal.get("tasks")
    passed = (
        isinstance(tasks, list)
        and bool(tasks)
        and observe.get("verdict") == "pass"
        and observe.get("ready_for_acceptance_generation") is True
    )
    print(json.dumps({"next": "exit" if passed else "continue"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

