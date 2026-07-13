"""根据步骤设计 observation 写入 ReAct route 决策。"""

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


def list_value(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    return value if isinstance(value, list) else []


def decide(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    observation = read_json(lgwf_dir / "step_design_observation.json")
    analysis = read_json(lgwf_dir / "step_design_decision_analysis.json")
    passed = observation.get("passed") is True
    next_value = "exit" if passed else "continue"
    default_reason = "step designs observation passed" if passed else "step designs observation still has blocking issues"
    reason = str(analysis.get("reason", "")).strip() or default_reason
    result = {
        "next": next_value,
        "passed": passed,
        "reason": reason,
        "recommended_next": analysis.get("recommended_next", ""),
        "issue_signatures": list_value(observation, "issue_signatures"),
        "repeat_issue_signatures": list_value(analysis, "repeat_issue_signatures"),
        "no_progress_risk": analysis.get("no_progress_risk") is True,
        "observation_file": ".lgwf/step_design_observation.json",
        "decision_analysis_file": ".lgwf/step_design_decision_analysis.json",
    }
    write_json(lgwf_dir / "step_designs_proposal_decision.json", result)
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
