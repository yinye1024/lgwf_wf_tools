from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    data = json.loads(sys.stdin.read() or "{}")
    context = {
        "stage": "confirm_requirements",
        "proposal": data,
        "decision_options": ["approve", "reject"],
        "review_focus": [
            "源 skill 与输出目录是否明确",
            "是否把运行状态边界固定为 ws/.lgwf",
            "是否避免在需求阶段发明实现细节",
        ],
    }
    json.dump(context, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
