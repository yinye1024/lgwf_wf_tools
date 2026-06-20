from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path.cwd() / ".lgwf" / "react_task_context.json"
    if not path.exists():
        raise SystemExit("missing .lgwf/react_task_context.json")
    context = json.loads(path.read_text(encoding="utf-8"))
    if context.get("all_done") is True:
        print(json.dumps({"lgwf_plan.execute_inputs_valid": True, "all_done": True}, ensure_ascii=False))
        return
    if not context.get("task") or not context.get("acceptance"):
        raise SystemExit("execute context requires task and acceptance")
    print(json.dumps({"lgwf_plan.execute_inputs_valid": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()

