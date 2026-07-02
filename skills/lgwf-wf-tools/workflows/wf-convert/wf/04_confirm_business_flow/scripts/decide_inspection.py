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
    inspection = load_json(root / ".lgwf" / "prompt_workflow_inspection.json")
    observe = load_json(root / ".lgwf" / "prompt_workflow_inspection_observe.json")
    has_required = all(key in inspection for key in ("source_summary", "detected_stages", "prompt_contracts"))
    passed = has_required and observe.get("verdict", "pass") == "pass"
    print(json.dumps({"next": "exit" if passed else "continue"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

