"""在 FOREACH child 中物化当前 implementation unit 的 Codex 上下文。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def ensure_target_dirs(target_dirs: list[str], target_files: list[str]) -> None:
    for raw_dir in target_dirs:
        Path(raw_dir).mkdir(parents=True, exist_ok=True)
    for raw_file in target_files:
        Path(raw_file).parent.mkdir(parents=True, exist_ok=True)


def build_current_implementation_unit_context(root: Path, unit: dict[str, Any]) -> dict[str, Any]:
    target_files = string_list(unit.get("target_files", []))
    target_dirs = string_list(unit.get("target_dirs", []))
    ensure_target_dirs(target_dirs, target_files)
    context = {
        "current_implementation_unit": unit,
        "current_implementation_unit_target_files": target_files,
        "current_implementation_unit_target_dirs": target_dirs,
        "instructions": [
            "只处理 current_implementation_unit 指定的目标目录和文件。",
            "优先处理 current_implementation_unit.repair_focus 中的 observe 失败项。",
            "如果目标实现需要扩大到其他 unit，输出 blocked_reason，不要擅自修改。",
        ],
    }
    write_json(root / ".lgwf" / "current_implementation_unit_context.json", context)
    return context


def main() -> None:
    context = build_current_implementation_unit_context(Path.cwd(), read_payload())
    print(
        json.dumps(
            {
                "lgwf_wf_create.current_implementation_unit_context": context,
                "lgwf_wf_create.current_implementation_unit_target_files": context[
                    "current_implementation_unit_target_files"
                ],
                "lgwf_wf_create.current_implementation_unit_target_dirs": context[
                    "current_implementation_unit_target_dirs"
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
