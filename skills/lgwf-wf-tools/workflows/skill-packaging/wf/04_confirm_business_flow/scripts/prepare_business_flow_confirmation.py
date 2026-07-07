from __future__ import annotations

import json
import sys


def main() -> None:
    proposal = json.loads(sys.stdin.read() or "{}")
    payload = {
        "stage": "confirm_packaging_plan",
        "proposal": proposal,
        "decision_options": ["approve", "reject"],
        "review_focus": [
            "目录结构是否符合 scaffold_template_spec",
            "是否保留脚本化稳定动作边界",
            "是否避免把运行状态写入源码树",
        ],
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
