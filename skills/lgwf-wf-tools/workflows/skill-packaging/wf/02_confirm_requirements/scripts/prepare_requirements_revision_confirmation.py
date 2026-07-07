from __future__ import annotations

import json
import sys


def main() -> None:
    proposal = json.loads(sys.stdin.read() or "{}")
    payload = {
        "stage": "confirm_requirements_revision",
        "proposal": proposal,
        "notes": "当前初稿未启用 revise 路由；本脚本位保留给后续评审闭环扩展。",
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
