"""为实现 ReAct 首轮准备空 observe 反馈文件。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def initialize(work_dir: Path) -> dict[str, Any]:
    path = work_dir / ".lgwf" / "implementation_observe.json"
    if path.exists():
        return {"initialized": False, "path": str(path), "reason": "existing observe feedback preserved"}
    payload = {
        "passed": False,
        "initial": True,
        "failures": ["首轮尚未执行 authoring audit"],
        "audit": {"ok": False, "skipped": True, "stdout": "", "stderr": "", "exit_code": None},
    }
    write_json(path, payload)
    return {"initialized": True, "path": str(path)}


def main() -> None:
    result = initialize(Path.cwd())
    print(json.dumps({"lgwf_wf_create.initialize_implementation_observe": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
