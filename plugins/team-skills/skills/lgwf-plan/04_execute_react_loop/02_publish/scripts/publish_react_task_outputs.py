from __future__ import annotations

import json
from pathlib import Path


def load(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    root = Path.cwd()
    context = load(root / ".lgwf" / "react_task_context.json", {})
    result = load(root / ".lgwf" / "react_task_result.json", {})
    summary = {
        "task_id": (context.get("task") or {}).get("task_id") or result.get("task_id"),
        "verdict": result.get("verdict"),
        "pass": result.get("pass"),
        "required_follow_up": result.get("required_follow_up", []),
    }
    report_dir = root / "reports" / "react-task"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "react_task_run_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"lgwf_plan.current_review": summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()

