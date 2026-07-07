from __future__ import annotations

import json
import sys


def main() -> None:
    data = json.loads(sys.stdin.read() or "{}")
    payload = {
        "stage": "confirm_step_designs_revision",
        "proposal": data,
        "notes": "当前版本先使用 approve/reject；该脚本位为未来 revise 保留。",
    }
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
