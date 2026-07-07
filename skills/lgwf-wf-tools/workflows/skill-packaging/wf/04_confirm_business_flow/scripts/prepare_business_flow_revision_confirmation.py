from __future__ import annotations

import json
import sys


def main() -> None:
    proposal = json.loads(sys.stdin.read() or "{}")
    payload = {
        "stage": "confirm_packaging_plan_revision",
        "proposal": proposal,
        "notes": "当前版本先使用二元审批；该脚本位保留给 revise 闭环。",
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
