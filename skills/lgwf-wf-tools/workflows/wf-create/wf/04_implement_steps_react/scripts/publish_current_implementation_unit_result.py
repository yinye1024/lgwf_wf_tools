"""校验并发布单个 implementation unit 的 staging 输出。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path, PurePosixPath
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"缺少单 unit 实现结果文件: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("单 unit 实现结果必须是 JSON object")
    return data


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def normalize_output_path(raw_path: str, *, allow_root: bool = False) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
    if cleaned.startswith("docs/steps/"):
        cleaned = f"wf/{cleaned}"
    path = PurePosixPath(cleaned)
    if not cleaned or path.is_absolute() or ":" in cleaned:
        raise ValueError(f"非法 unit 输出路径: {raw_path}")
    if any(part in {"..", ".lgwf"} for part in path.parts):
        raise ValueError(f"非法 unit 输出路径: {raw_path}")
    normalized = path.as_posix().strip("/")
    if normalized == "." and not allow_root:
        raise ValueError(f"非法 unit 输出文件路径: {raw_path}")
    return normalized


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


def target_package_root(root: Path, context: dict[str, Any]) -> Path:
    implementation_context = load_json(root / ".lgwf" / "implementation_context.json")
    target_from_context = str(context.get("target_package_abs", "")).strip()
    target_from_run = str(implementation_context.get("target_package_abs", "")).strip()
    target_raw = target_from_context or target_from_run
    if not target_raw:
        raise ValueError("缺少 target_package_abs，无法发布 implementation unit")
    target_abs = Path(target_raw).resolve()
    if target_from_run and target_abs != Path(target_from_run).resolve():
        raise ValueError("current unit target_package_abs 与 implementation_context.json 不一致")
    workspace_root_raw = str(implementation_context.get("workspace_root", "")).strip()
    if workspace_root_raw:
        ensure_within(target_abs, Path(workspace_root_raw).resolve(), "target_package_abs")
    return target_abs


def output_files_from_context(context: dict[str, Any]) -> list[str]:
    output_files = string_list(context.get("output_files", []))
    if not output_files:
        unit = context.get("current_implementation_unit", {})
        if isinstance(unit, dict):
            output_files = (
                string_list(unit.get("output_files", []))
                or string_list(unit.get("package_relative_files", []))
                or string_list(unit.get("planned_files", []))
            )
    return unique([normalize_output_path(path) for path in output_files])


def output_dirs_from_context(context: dict[str, Any], output_files: list[str]) -> list[str]:
    output_dirs = string_list(context.get("output_dirs", []))
    if not output_dirs:
        unit = context.get("current_implementation_unit", {})
        if isinstance(unit, dict):
            output_dirs = (
                string_list(unit.get("output_dirs", []))
                or string_list(unit.get("package_relative_dirs", []))
                or string_list(unit.get("planned_dirs", []))
            )
    result = [normalize_output_path(path, allow_root=True) for path in output_dirs]
    for output_file in output_files:
        parent = PurePosixPath(output_file).parent.as_posix()
        result.append("." if parent == "." else parent)
    return unique(result)


def generated_file_paths(result: dict[str, Any]) -> list[str]:
    raw_items = result.get("generated_files", [])
    paths: list[str] = []
    if isinstance(raw_items, list):
        for item in raw_items:
            if isinstance(item, dict):
                raw_path = str(item.get("path", "")).strip()
            else:
                raw_path = str(item).strip()
            if raw_path:
                paths.append(normalize_output_path(raw_path))
    return unique(paths)


def stage_files(unit_output_abs: Path) -> list[str]:
    if not unit_output_abs.is_dir():
        return []
    result: list[str] = []
    for path in unit_output_abs.rglob("*"):
        if path.is_file():
            result.append(path.relative_to(unit_output_abs).as_posix())
    return sorted(result)


def publish_current_implementation_unit_result(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    context = load_json(lgwf_dir / "current_implementation_unit_context.json")
    result_path = lgwf_dir / "current_implementation_unit_result.json"
    result = load_json(result_path)
    status = str(result.get("status", "")).lower()
    if status in {"failed", "error"}:
        return result

    output_files = output_files_from_context(context)
    output_dirs = output_dirs_from_context(context, output_files)
    unit_output_dir = str(context.get("unit_output_dir", "")).strip()
    if not unit_output_dir:
        raise ValueError("缺少 unit_output_dir，无法发布 implementation unit")
    unit_output_abs = ensure_within(root / unit_output_dir, root / ".lgwf" / "implementation_stage", "unit_output_dir")
    target_abs = target_package_root(root, context)

    output_file_set = set(output_files)
    staged_files = stage_files(unit_output_abs)
    unexpected = [path for path in staged_files if path not in output_file_set]
    if unexpected:
        raise ValueError(f"staging 目录包含 output_files 外文件: {unexpected}")

    for output_dir in output_dirs:
        rel_dir = "" if output_dir == "." else output_dir
        ensure_within(target_abs / rel_dir, target_abs, "target_output_dir").mkdir(parents=True, exist_ok=True)

    generated_paths = generated_file_paths(result)
    generated_outside_manifest = [path for path in generated_paths if path not in output_file_set]
    if generated_outside_manifest:
        raise ValueError(f"generated_files 包含 output_files 外路径: {generated_outside_manifest}")
    staged_file_set = set(staged_files)
    publishable_files = [path for path in output_files if path in staged_file_set]
    missing = [path for path in output_files if path not in staged_file_set]
    published: list[dict[str, str]] = []
    for rel_path in publishable_files:
        source_path = ensure_within(unit_output_abs / rel_path, unit_output_abs, "staging_source_file")
        target_path = ensure_within(target_abs / rel_path, target_abs, "target_output_file")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        published.append(
            {
                "path": rel_path,
                "source": (Path(unit_output_dir) / rel_path).as_posix(),
                "target": str(target_path),
            }
        )

    if missing:
        risks = result.get("remaining_risks", [])
        if not isinstance(risks, list):
            risks = []
        risks.extend(f"staging 缺少声明输出文件: {path}" for path in missing)
        result["remaining_risks"] = unique([str(item) for item in risks if str(item).strip()])
        if status == "ok":
            result["status"] = "partial" if published else "failed"

    result["published_files"] = published
    if published:
        result["generated_files"] = [{"path": item["path"]} for item in published]
    return result


def main() -> None:
    result = publish_current_implementation_unit_result(Path.cwd())
    print(
        json.dumps(
            {"lgwf_wf_create.current_implementation_unit_result": result},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
