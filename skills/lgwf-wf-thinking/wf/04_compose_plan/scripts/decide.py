from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    observation = read_json(lgwf_dir / "composition_plan_observe.json")
    score = observation.get("quality_score", 0)
    try:
        score_value = float(score)
    except (TypeError, ValueError):
        score_value = 0.0
    passed = bool(observation.get("passed")) and score_value >= 0.72
    result: dict[str, Any] = {
        "passed": passed,
        "continue": not passed,
        "quality_score": score_value,
        "issues": observation.get("issues", []),
        "required_revisions": observation.get("required_revisions", []),
    }
    print(json.dumps({"lgwf_wf_thinking.compose_decision": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
