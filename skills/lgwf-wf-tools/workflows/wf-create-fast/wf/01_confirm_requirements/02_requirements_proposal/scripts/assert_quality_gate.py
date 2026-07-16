"""确保需求 proposal 质量闸最终通过。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def failure_messages(gate: dict[str, Any]) -> list[str]:
    checks = gate.get("checks")
    if not isinstance(checks, list):
        return ["quality gate checks missing"]
    messages = [
        str(item.get("message", ""))
        for item in checks
        if isinstance(item, dict) and item.get("passed") is not True
    ]
    return [message for message in messages if message] or ["quality gate failed"]


def main() -> None:
    gate = read_json(Path.cwd() / ".lgwf" / "create_requirements_proposal_quality_gate.json")
    if gate.get("passed") is not True:
        raise ValueError("requirements proposal quality gate failed after ReAct repair: " + "; ".join(failure_messages(gate)))
    print(json.dumps({"lgwf_wf_create_fast.requirements_proposal_quality_gate_asserted": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
