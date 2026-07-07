from __future__ import annotations

import json
import sys


def main() -> None:
    materialized = json.loads(sys.stdin.read() or "{}")
    result = {
        "passed": False,
        "summary": "当前只完成 workflow 初稿脚手架，尚未实现真实打包产物与 audit smoke。",
        "issues": [
            "vendor runtime 尚未落盘",
            "runner/manifest 尚未生成",
            "需要后续实现真实复制与 audit 流程",
        ],
        "materialized_package": materialized,
    }
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
