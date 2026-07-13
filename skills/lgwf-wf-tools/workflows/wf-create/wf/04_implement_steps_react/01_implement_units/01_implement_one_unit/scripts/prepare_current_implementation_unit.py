"""在 FOREACH child 中物化当前 implementation unit 的 staging 输出上下文。"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
from typing import Any

STAGING_ROOT = Path(".lgwf") / "implementation_stage"
SENSITIVE_UNIT_FIELDS = {"target_package_abs", "workspace_root"}
SCHEMA_RESOURCE = Path(__file__).resolve().parents[1] / "resources" / "codex_output_schemas.json"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def load_schema_registry() -> dict[str, Any]:
    if not SCHEMA_RESOURCE.is_file():
        return {}
    data = json.loads(SCHEMA_RESOURCE.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def safe_unit_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip()).strip("._-")
    return cleaned or "unit"


def normalize_output_path(raw_path: str, *, allow_root: bool = False) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned or path.is_absolute() or ":" in cleaned:
        raise ValueError(f"非法 unit 输出路径: {raw_path}")
    if any(part in {"..", ".lgwf"} for part in path.parts):
        raise ValueError(f"非法 unit 输出路径: {raw_path}")
    normalized = path.as_posix().strip("/")
    if normalized == "." and not allow_root:
        raise ValueError(f"非法 unit 输出文件路径: {raw_path}")
    return normalized


def normalize_output_files(unit: dict[str, Any]) -> list[str]:
    raw_files = (
        string_list(unit.get("output_files", []))
        or string_list(unit.get("package_relative_files", []))
        or string_list(unit.get("planned_files", []))
    )
    return unique([normalize_output_path(path) for path in raw_files])


def normalize_output_dirs(unit: dict[str, Any], output_files: list[str]) -> list[str]:
    raw_dirs = (
        string_list(unit.get("output_dirs", []))
        or string_list(unit.get("package_relative_dirs", []))
        or string_list(unit.get("planned_dirs", []))
    )
    dirs = [normalize_output_path(path, allow_root=True) for path in raw_dirs]
    for output_file in output_files:
        parent = PurePosixPath(output_file).parent.as_posix()
        dirs.append("." if parent == "." else parent)
    return unique(dirs)


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def ensure_within(path: Path, parent: Path, label: str) -> Path:
    resolved = path.resolve()
    resolved_parent = parent.resolve()
    if resolved != resolved_parent and not resolved.is_relative_to(resolved_parent):
        raise ValueError(f"{label} 越过允许目录: {resolved} 不在 {resolved_parent} 下")
    return resolved


def workspace_rel(path: Path) -> str:
    return path.as_posix()


def sanitized_unit(unit: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in unit.items() if key not in SENSITIVE_UNIT_FIELDS}


def prepare_staging(
    root: Path,
    unit_output_dir: str,
    output_dirs: list[str],
    output_files: list[str],
    target_package_abs: str,
) -> tuple[list[str], list[str]]:
    staging_root_abs = (root / STAGING_ROOT).resolve()
    unit_output_abs = ensure_within(root / unit_output_dir, staging_root_abs, "unit_output_dir")
    if unit_output_abs.exists():
        shutil.rmtree(unit_output_abs)
    unit_output_abs.mkdir(parents=True, exist_ok=True)

    workspace_output_dirs: list[str] = []
    for output_dir in output_dirs:
        rel_dir = "" if output_dir == "." else output_dir
        output_path = ensure_within(unit_output_abs / rel_dir, unit_output_abs, "workspace_output_dir")
        output_path.mkdir(parents=True, exist_ok=True)
        workspace_output_dirs.append(workspace_rel(Path(unit_output_dir) / rel_dir) if rel_dir else unit_output_dir)

    target_abs = Path(target_package_abs).resolve() if target_package_abs else None
    workspace_output_files: list[str] = []
    for output_file in output_files:
        output_path = ensure_within(unit_output_abs / output_file, unit_output_abs, "workspace_output_file")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        workspace_output_files.append(workspace_rel(Path(unit_output_dir) / output_file))
        if target_abs is None:
            continue
        source_path = ensure_within(target_abs / output_file, target_abs, "target_source_file")
        if source_path.is_file():
            shutil.copy2(source_path, output_path)
    return unique(workspace_output_dirs), workspace_output_files


def output_file_schemas(output_files: list[str], schema_registry: dict[str, Any]) -> dict[str, Any]:
    raw_schemas = schema_registry.get("target_package_output_file_schemas", {})
    if not isinstance(raw_schemas, dict):
        return {}
    return {
        output_file: raw_schemas[output_file]
        for output_file in output_files
        if output_file in raw_schemas and isinstance(raw_schemas[output_file], dict)
    }


def codex_output_schema(schema_registry: dict[str, Any]) -> dict[str, Any]:
    raw_schemas = schema_registry.get("codex_output_json_schemas", {})
    schema = raw_schemas.get(".lgwf/current_implementation_unit_result.json", {}) if isinstance(raw_schemas, dict) else {}
    return schema if isinstance(schema, dict) else {}


def build_current_implementation_unit_context(root: Path, unit: dict[str, Any]) -> dict[str, Any]:
    unit_id = str(unit.get("unit_id", "")).strip() or "unit"
    output_files = normalize_output_files(unit)
    output_dirs = normalize_output_dirs(unit, output_files)
    target_package_abs = str(unit.get("target_package_abs", "")).strip()
    safe_id = safe_unit_id(unit_id)
    unit_output_dir = workspace_rel(STAGING_ROOT / safe_id)
    workspace_output_dirs, workspace_output_files = prepare_staging(
        root,
        unit_output_dir,
        output_dirs,
        output_files,
        target_package_abs,
    )
    schema_registry = load_schema_registry()
    context = {
        "current_implementation_unit": sanitized_unit(unit),
        "unit_id": unit_id,
        "unit_output_dir": unit_output_dir,
        "output_files": output_files,
        "output_dirs": output_dirs,
        "workspace_output_files": workspace_output_files,
        "workspace_output_dirs": workspace_output_dirs,
        "codex_output_json_schema": codex_output_schema(schema_registry),
        "target_output_file_schemas": output_file_schemas(output_files, schema_registry),
        "instructions": [
            "只处理 current_implementation_unit 指定的输出文件。",
            "只能写入 unit_output_dir 下的 workspace_output_files，保持 output_files 的 package 相对路径结构。",
            "不要直接写最终目标 package；发布脚本会把 unit_output_dir 中的文件复制到目标 package。",
            "生成 JSON 输出文件时只能使用 target_output_file_schemas 中随当前 context 提供的 schema；缺少 schema 时记录 blocked_reason，不要递归搜索 .lgwf 或读取宿主仓库样例。",
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
                "lgwf_wf_create.current_implementation_unit_output_files": context["output_files"],
                "lgwf_wf_create.current_implementation_unit_output_dirs": context["output_dirs"],
                "lgwf_wf_create.current_implementation_unit_output_dir": context["unit_output_dir"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
