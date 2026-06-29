from __future__ import annotations

import json
from pathlib import Path


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def main() -> None:
    root = Path.cwd()
    proposal = load(root / ".lgwf" / "react_task_plan_proposal.json")
    observe = load(root / ".lgwf" / "react_task_plan_observe.json")
    ok = bool(proposal.get("tasks")) and observe.get("verdict") == "pass"
    direction = {
        "status": "ready_for_acceptance" if ok else "plan_generation_failed",
        "allowed_directions": ["retry_generation", "adjust_request", "stop"] if not ok else [],
        "issues": observe.get("issues", []),
        "required_changes": observe.get("required_changes", []),
    }
    path = root / ".lgwf" / "react_task_plan_generation_direction.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(direction, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"lgwf_plan.plan_generation_direction": direction}, ensure_ascii=False))


if __name__ == "__main__":
    main()

