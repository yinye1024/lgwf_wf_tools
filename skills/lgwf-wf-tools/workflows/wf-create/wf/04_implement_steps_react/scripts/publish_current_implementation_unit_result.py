"""把单个 implementation unit 的 Codex JSON 文件发布回当前 FOREACH 输出 state。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"缺少单 unit 实现结果文件: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("单 unit 实现结果必须是 JSON object")
    return data


def main() -> None:
    result = load_json(Path.cwd() / ".lgwf" / "current_implementation_unit_result.json")
    print(
        json.dumps(
            {"lgwf_wf_create.current_implementation_unit_result": result},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
