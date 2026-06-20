from __future__ import annotations

import json
from pathlib import Path


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def main() -> None:
    result = load(Path.cwd() / ".lgwf" / "react_task_result.json")
    passed = result.get("pass") is True or result.get("verdict") == "pass"
    print(json.dumps({"next": "exit" if passed else "continue"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

