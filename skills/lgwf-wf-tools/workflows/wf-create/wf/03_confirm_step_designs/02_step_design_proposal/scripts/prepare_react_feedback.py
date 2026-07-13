"""初始化步骤设计 proposal ReAct 的空反馈文件。"""

from __future__ import annotations

import json
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    write_json(
        lgwf_dir / "step_design_observation.json",
        {
            "passed": False,
            "verdict": "not_started",
            "structural_passed": False,
            "semantic_passed": False,
            "blocking_issues": [],
            "failed_checks": [],
            "issue_signatures": [],
            "valid_parts_to_preserve": [],
            "reason_feedback": {
                "repair_mode": "first_round",
                "priority_issue_ids": [],
                "must_preserve": [],
                "must_change": [],
                "forbidden_changes": ["不得写入 .lgwf/step_designs.json"],
                "act_instruction_patch": [],
            },
        },
    )
    write_json(lgwf_dir / "step_designs_proposal_quality_gate.json", {})
    write_json(lgwf_dir / "step_designs_proposal_decision.json", {})
    print(
        json.dumps(
            {
                "prepared": True,
                "files": [
                    ".lgwf/step_design_observation.json",
                    ".lgwf/step_designs_proposal_quality_gate.json",
                    ".lgwf/step_designs_proposal_decision.json",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
