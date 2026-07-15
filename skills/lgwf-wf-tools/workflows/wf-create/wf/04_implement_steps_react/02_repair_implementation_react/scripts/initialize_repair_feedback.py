"""初始化 repair ReAct 首轮反馈文件。"""

from __future__ import annotations

import json
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    decision = {
        "next": "continue",
        "passed": False,
        "reason": "initial repair iteration",
        "source": "initialize_repair_feedback",
        "status": "not_started",
        "needs_post_fix": False,
        "failures": [],
    }
    analysis = {
        "recommended_next": "continue",
        "reason": "initial repair iteration",
        "failure_signatures": [],
        "repeat_issue_signatures": [],
        "no_progress_risk": False,
    }
    write_json(lgwf_dir / "implementation_decision.json", decision)
    write_json(lgwf_dir / "implementation_repair_decision_analysis.json", analysis)
    print(
        json.dumps(
            {
                "lgwf_wf_create.initialize_repair_feedback_result": {
                    "prepared": True,
                    "files": [
                        ".lgwf/implementation_decision.json",
                        ".lgwf/implementation_repair_decision_analysis.json",
                    ],
                }
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
