"""准备修复优化 ACT slot 的最小上下文。"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


STAGING_ROOT = Path(".lgwf") / "implementation_repair_stage"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_package_path(raw_path: str) -> str:
    cleaned = str(raw_path).strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned or cleaned == ".":
        raise ValueError("repair target file 不能为空")
    if path.is_absolute() or ":" in cleaned or any(part == ".." for part in path.parts):
        raise ValueError(f"repair target file 必须是 package-relative path: {raw_path}")
    if path.parts and path.parts[0] == ".lgwf":
        raise ValueError(f"repair target file 不得写入 .lgwf: {raw_path}")
    return path.as_posix()


def repair_target_files(repair_reason: dict[str, Any]) -> list[str]:
    repair_units = repair_reason.get("repair_units", [])
    if not isinstance(repair_units, list):
        return []
    output_files: list[str] = []
    for unit in repair_units:
        if not isinstance(unit, dict):
            continue
        raw_targets = unit.get("target_files", [])
        if not isinstance(raw_targets, list):
            continue
        for target in raw_targets:
            output_files.append(normalize_package_path(str(target)))
    return unique(output_files)


def build_repair_context(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    implementation_context = read_json(lgwf_dir / "implementation_context.json")
    repair_reason = read_json(lgwf_dir / "implementation_repair_reason.json")
    repair_required = repair_reason.get("repair_required") is True
    target_files = repair_target_files(repair_reason) if repair_required else []
    workspace_output_files = [(STAGING_ROOT / target_file).as_posix() for target_file in target_files]
    workspace_output_dirs = unique(
        [
            PurePosixPath(output_file).parent.as_posix()
            for output_file in workspace_output_files
            if PurePosixPath(output_file).parent.as_posix() != "."
        ]
    )
    context = {
        "repair_required": repair_required,
        "repair_reason": repair_reason,
        "target_package_root": implementation_context.get("target_package_root", ""),
        "unit_output_dir": STAGING_ROOT.as_posix(),
        "target_files": target_files,
        "workspace_output_files": workspace_output_files,
        "workspace_output_dirs": workspace_output_dirs,
        "instructions": [
            "只修复 target_files 中列出的 package-relative 文件。",
            "只能写 workspace_output_files；不要直接写 target_package_abs。",
            "如果 repair_required=false，输出 no_op=true，不写 staged files。",
        ],
    }
    (root / STAGING_ROOT).mkdir(parents=True, exist_ok=True)
    write_json(lgwf_dir / "implementation_repair_context.json", context)
    return context


def main() -> None:
    result = build_repair_context(Path.cwd())
    print(json.dumps({"lgwf_wf_create.prepare_repair_context_result": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
