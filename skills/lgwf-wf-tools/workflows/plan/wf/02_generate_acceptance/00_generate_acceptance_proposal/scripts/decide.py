from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def main() -> None:
    root = Path.cwd()
    acceptance = load_json(root / ".lgwf" / "react_acceptance_proposal.json")
    observe = load_json(root / ".lgwf" / "react_acceptance_observe.json")
    passed = (
        isinstance(acceptance.get("tasks"), list)
        and bool(acceptance["tasks"])
        and observe.get("verdict") == "pass"
        and observe.get("acceptance_is_executable") is True
        and observe.get("plan_validation_map_complete") is True
        and observe.get("ready_for_confirmation") is True
        and not observe.get("issues")
        and not observe.get("required_changes")
    )
    print(json.dumps({"next": "exit" if passed else "continue"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

