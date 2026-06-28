from __future__ import annotations

import json
from pathlib import Path


def load(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> None:
    root = Path.cwd()
    plan = load(root / ".lgwf" / "react_task_plan.json", {})
    history = load(root / ".lgwf" / "react_task_history.json", [])
    report = {
        "current_task_id": plan.get("current_task_id"),
        "tasks": plan.get("tasks", []),
        "history_count": len(history) if isinstance(history, list) else 0,
    }
    report_dir = root / "reports" / "react-task"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "react_task_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# React Task Report", "", f"- current_task_id: {report['current_task_id']}", f"- history_count: {report['history_count']}"]
    (report_dir / "react_task_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"lgwf_plan.finished": report.get("current_task_id") is None, "lgwf_plan.report": report}, ensure_ascii=False))


if __name__ == "__main__":
    main()

