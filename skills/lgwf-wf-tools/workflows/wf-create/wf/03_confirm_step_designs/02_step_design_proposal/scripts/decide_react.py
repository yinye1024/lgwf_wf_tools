"""根据步骤设计 proposal 质量闸决定 ReAct 是否继续。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def failed_checks(gate: dict[str, Any]) -> list[dict[str, Any]]:
    checks = gate.get("checks")
    if not isinstance(checks, list):
        return []
    return [
        {
            "name": str(item.get("name", "")),
            "message": str(item.get("message", "")),
        }
        for item in checks
        if isinstance(item, dict) and item.get("passed") is not True
    ]


def decide(root: Path) -> dict[str, Any]:
    gate = read_json(root / ".lgwf" / "step_designs_proposal_quality_gate.json")
    passed = gate.get("passed") is True
    failures = failed_checks(gate)
    result = {
        "next": "exit" if passed else "continue",
        "passed": passed,
        "reason": "step designs proposal quality gate passed"
        if passed
        else "step designs proposal quality gate failed; continue proposal repair",
        "failed_checks": failures,
        "quality_gate_file": ".lgwf/step_designs_proposal_quality_gate.json",
    }
    write_json(root / ".lgwf" / "step_designs_proposal_decision.json", result)
    return result


def main() -> None:
    result = decide(Path.cwd())
    print(
        json.dumps(
            {
                "next": result["next"],
                "lgwf_wf_create.step_designs_proposal_decision": result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
