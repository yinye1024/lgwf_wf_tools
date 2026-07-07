from __future__ import annotations

import json
import sys


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        payload = {}
    else:
        payload = json.loads(raw)
    if isinstance(payload, str):
        payload = {"raw_intent": payload}
    if not isinstance(payload, dict):
        payload = {"value": payload}

    normalized = {
        "workflow_name": payload.get("workflow_name", "LGWF Skill Packaging Workflow"),
        "source_skill": payload.get("source_skill", "<source-skill>"),
        "output_parent": payload.get("output_parent", "<output-parent>"),
        "force": bool(payload.get("force", False)),
        "constraints": [
            "wf/ 是唯一 workflow root",
            "运行状态只写入 ws/.lgwf",
            "稳定动作优先使用脚本而不是 Agent 直接落盘",
        ],
    }
    json.dump(normalized, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
