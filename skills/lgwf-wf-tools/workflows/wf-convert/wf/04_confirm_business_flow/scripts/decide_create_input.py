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
    proposal = load_json(root / ".lgwf" / "wf_create_input_proposal.json")
    observe = load_json(root / ".lgwf" / "wf_create_input_observe.json")
    has_required = all(key in proposal for key in ("workflow_name", "target_package_root", "raw_intent"))
    passed = has_required and observe.get("verdict", "pass") == "pass"
    print(json.dumps({"next": "exit" if passed else "continue"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

