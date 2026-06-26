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
    approval = read_json(lgwf_dir / "react_task_contract_approval.json")
    decision = str(approval.get("approval") or approval.get("decision") or approval.get("status") or "unknown").strip().lower()
    status = "contract_revision_requested" if decision in {"revise", "reject"} else "contract_not_approved"
    report = {
        "status": status,
        "decision": decision,
        "comment": approval.get("comment", ""),
        "executed": False,
        "reason": "用户未批准当前计划与验收契约，workflow 正常结束且不进入执行阶段。",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(lgwf_dir / "contract_review_finish.json", report)
    print(json.dumps({"lgwf_plan.contract_review_finished": True, "lgwf_plan.contract_review_finish": report}, ensure_ascii=False))


if __name__ == "__main__":
    main()
