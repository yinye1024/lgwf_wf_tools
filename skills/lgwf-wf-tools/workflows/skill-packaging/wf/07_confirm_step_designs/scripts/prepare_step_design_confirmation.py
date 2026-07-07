from __future__ import annotations

import json
import sys


def main() -> None:
    data = json.loads(sys.stdin.read() or "{}")
    payload = {
        "stage": "confirm_step_designs",
        "proposal": data,
        "decision_options": ["approve", "reject"],
        "review_focus": [
            "是否只覆盖已批准步骤",
            "是否保留 tests、wf/docs/steps 和四个第一层阶段",
            "是否没有生成根 SKILL.md 或根 workflow.lgwf",
        ],
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
