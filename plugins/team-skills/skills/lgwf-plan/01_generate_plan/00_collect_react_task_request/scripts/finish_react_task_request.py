from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    decision = read_json(lgwf_dir / "react_task_request.json")
    report = {
        "status": "task_request_rejected",
        "decision": str(decision.get("approval") or decision.get("decision") or "reject").strip().lower(),
        "comment": decision.get("comment", ""),
        "plan_generation_started": False,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(lgwf_dir / "react_task_request_finish.json", report)
    print(json.dumps({"lgwf_plan.task_request_finished": True, "lgwf_plan.task_request_finish": report}, ensure_ascii=False))


if __name__ == "__main__":
    main()
