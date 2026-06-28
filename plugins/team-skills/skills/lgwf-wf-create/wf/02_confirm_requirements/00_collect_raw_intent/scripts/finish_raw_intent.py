"""同步原始意图产物到 state，并结束该阶段。"""

from __future__ import annotations

import json
from pathlib import Path


def load_raw_intent_request(root: Path) -> dict:
    path = root / ".lgwf" / "raw_intent_request.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def main() -> None:
    print(
        json.dumps(
            {
                "lgwf_wf_create.raw_intent_request": load_raw_intent_request(Path.cwd()),
                "lgwf_wf_create.raw_intent_finished": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
