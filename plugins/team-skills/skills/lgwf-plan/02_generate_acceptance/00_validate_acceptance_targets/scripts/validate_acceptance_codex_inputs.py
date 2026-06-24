from __future__ import annotations

import json
from pathlib import Path


def read(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing required artifact: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit(f"artifact must be an object: {path}")
    return data


def main() -> None:
    root = Path.cwd()
    plan = read(root / ".lgwf" / "react_task_plan_proposal.json")
    observe = read(root / ".lgwf" / "react_task_plan_observe.json")
    issues = []
    if not isinstance(plan.get("tasks"), list) or not plan["tasks"]:
        issues.append("plan proposal requires non-empty tasks")
    if observe.get("verdict") != "pass":
        issues.append("plan observe must pass before acceptance generation")
    if issues:
        raise SystemExit("; ".join(issues))
    print(json.dumps({"lgwf_plan.acceptance_inputs_valid": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()

