from __future__ import annotations

import json
from pathlib import Path


def ensure_observe_feedback_placeholder() -> None:
    path = Path.cwd() / ".lgwf" / "react_task_result.json"
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "passed": False,
                "issues": [],
                "summary": "首轮默认 observe 占位文件；等待 OBSERVE 阶段写入真实验收结果。",
                "initial_placeholder": True,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    path = Path.cwd() / ".lgwf" / "react_task_context.json"
    if not path.exists():
        raise SystemExit("missing .lgwf/react_task_context.json")
    context = json.loads(path.read_text(encoding="utf-8-sig"))
    if context.get("all_done") is True:
        print(json.dumps({"lgwf_plan.execute_inputs_valid": True, "all_done": True}, ensure_ascii=False))
        return
    if not context.get("task") or not context.get("acceptance"):
        raise SystemExit("execute context requires task and acceptance")
    ensure_observe_feedback_placeholder()
    print(json.dumps({"lgwf_plan.execute_inputs_valid": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()

