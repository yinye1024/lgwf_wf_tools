"""根据 Contract observe 结果决定是否继续 ReAct。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def decide(work_dir: Path) -> dict[str, Any]:
    observe = read_json(work_dir / ".lgwf" / "contract_observe.json")
    passed = observe.get("passed") is True
    result = {
        "next": "exit" if passed else "continue",
        "passed": passed,
        "reason": "Contract checks and authoring audit passed"
        if passed
        else "Contract checks or authoring audit failed; continue Contract repair",
        "failures": observe.get("failures", []),
    }
    write_json(work_dir / ".lgwf" / "contract_decision.json", result)
    return result


def main() -> None:
    print(json.dumps(decide(Path.cwd()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
