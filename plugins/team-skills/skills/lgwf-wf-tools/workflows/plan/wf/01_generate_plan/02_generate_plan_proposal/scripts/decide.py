from __future__ import annotations

import json
import importlib.util
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def load_safety_validator():
    path = Path(__file__).resolve().with_name("plan_contract_safety.py")
    spec = importlib.util.spec_from_file_location("plan_contract_safety", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load plan_contract_safety.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    root = Path.cwd()
    request = load_json(root / ".lgwf" / "react_task_request.json")
    proposal = load_json(root / ".lgwf" / "react_task_plan_proposal.json")
    observe = load_json(root / ".lgwf" / "react_task_plan_observe.json")
    safety = load_safety_validator().validate_plan_contract(request, proposal)
    tasks = proposal.get("tasks")
    passed = (
        isinstance(tasks, list)
        and bool(tasks)
        and observe.get("verdict") == "pass"
        and observe.get("ready_for_acceptance_generation") is True
        and safety.get("passed") is True
    )
    print(json.dumps({"next": "exit" if passed else "continue", "plan_contract_safety": safety}, ensure_ascii=False))


if __name__ == "__main__":
    main()

