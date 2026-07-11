"""为实现 ReAct 首轮准备空 audit/observe/decision 反馈文件。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initialize(work_dir: Path) -> dict[str, Any]:
    lgwf_dir = work_dir / ".lgwf"
    audit_path = lgwf_dir / "implementation_audit_result.json"
    decision_path = lgwf_dir / "implementation_decision.json"
    observe_path = lgwf_dir / "implementation_observe.json"
    if audit_path.exists() and decision_path.exists() and observe_path.exists():
        return {
            "initialized": False,
            "audit_path": str(audit_path),
            "decision_path": str(decision_path),
            "observe_path": str(observe_path),
            "reason": "existing audit/observe/decision feedback preserved",
        }
    feedback_payload = {
        "passed": False,
        "status": "initial",
        "initial": True,
        "failures": ["首轮尚未执行 authoring audit"],
        "audit": {"ok": False, "skipped": True, "stdout": "", "stderr": "", "exit_code": None},
        "checks": [],
        "needs_post_fix": False,
    }
    decision_payload = {
        "next": "continue",
        "passed": False,
        "status": "initial",
        "initial": True,
        "reason": "initial implementation round; no previous decision",
        "source": "initialize_implementation_observe.py",
        "needs_post_fix": False,
        "failures": ["首轮尚未执行 implementation decide"],
    }
    if not audit_path.exists():
        write_json(audit_path, feedback_payload)
    if not decision_path.exists():
        write_json(decision_path, decision_payload)
    if not observe_path.exists():
        write_json(observe_path, feedback_payload)
    return {
        "initialized": True,
        "audit_path": str(audit_path),
        "decision_path": str(decision_path),
        "observe_path": str(observe_path),
    }


def main() -> None:
    result = initialize(Path.cwd())
    print(json.dumps({"lgwf_wf_create.initialize_implementation_observe": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
