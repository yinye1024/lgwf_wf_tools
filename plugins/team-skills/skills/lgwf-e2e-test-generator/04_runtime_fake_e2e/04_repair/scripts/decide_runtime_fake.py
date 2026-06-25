from __future__ import annotations

from pathlib import Path
import json


def main() -> None:
    path = Path(".lgwf/e2e_runtime_fake_observe.json")
    if not path.exists():
        print(json.dumps({"next": "continue", "lgwf_e2e.runtime_fake_validation": {"passed": False, "reason": "missing observe output"}}, ensure_ascii=False))
        return
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    passed = bool(data.get("passed"))
    print(json.dumps({"next": "exit" if passed else "continue", "lgwf_e2e.runtime_fake_validation": data}, ensure_ascii=False))


if __name__ == "__main__":
    main()
