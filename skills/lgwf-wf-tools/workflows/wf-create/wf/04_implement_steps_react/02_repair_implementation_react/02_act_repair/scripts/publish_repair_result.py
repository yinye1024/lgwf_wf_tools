"""发布修复 ACT 的 staging 文件，并更新 implementation_result。"""

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


def normalize_package_path(raw_path: str, field_name: str = "repair file") -> str:
    cleaned = str(raw_path).strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if path.is_absolute() or ":" in cleaned or any(part == ".." for part in path.parts):
        raise ValueError(f"{field_name} 必须是 package-relative path: {raw_path}")
    if path.parts and path.parts[0] == ".lgwf":
        raise ValueError(f"{field_name} 不得写入 .lgwf: {raw_path}")
    return path.as_posix()


def normalize_path_list(raw_items: Any, field_name: str) -> tuple[list[str], list[str]]:
    if not isinstance(raw_items, list):
        return [], [f"{field_name} 必须是 list"]
    result: list[str] = []
    failures: list[str] = []
    for index, item in enumerate(raw_items):
        if isinstance(item, dict):
            raw_path = item.get("path", "")
        else:
            raw_path = item
        try:
            path = normalize_package_path(str(raw_path), f"{field_name}[{index}]")
        except ValueError as exc:
            failures.append(str(exc))
            continue
        if path not in result:
            result.append(path)
    return result, failures


def normalize_generated_files(raw_files: Any) -> tuple[list[str], list[str]]:
    return normalize_path_list(raw_files, "generated_files")


def target_files_from_reason(repair_reason: dict[str, Any]) -> tuple[list[str], list[str]]:
    raw_top_level = repair_reason.get("target_files", [])
    if "target_files" in repair_reason and not isinstance(raw_top_level, list):
        return [], ["target_files 必须是 list"]
    if isinstance(raw_top_level, list) and raw_top_level:
        return normalize_path_list(raw_top_level, "target_files")
    repair_units = repair_reason.get("repair_units", [])
    if not isinstance(repair_units, list):
        return [], ["repair_units 必须是 list"]
    result: list[str] = []
    failures: list[str] = []
    for unit_index, unit in enumerate(repair_units):
        if not isinstance(unit, dict):
            failures.append(f"repair_units[{unit_index}] 必须是 object")
            continue
        paths, path_failures = normalize_path_list(
            unit.get("target_files", []),
            f"repair_units[{unit_index}].target_files",
        )
        failures.extend(path_failures)
        for path in paths:
            if path not in result:
                result.append(path)
    return result, failures


def merge_generated_files(existing: Any, published: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    if isinstance(existing, list):
        for item in existing:
            raw_path = item.get("path", "") if isinstance(item, dict) else item
            if not raw_path:
                continue
            path = normalize_package_path(str(raw_path))
            if path not in seen:
                seen.add(path)
                result.append({"path": path})
    for item in published:
        path = normalize_package_path(str(item.get("path", "")))
        if path not in seen:
            seen.add(path)
            result.append({"path": path})
    return result


def resolve_target_package(root: Path) -> Path:
    implementation_context = read_json(root / ".lgwf" / "implementation_context.json")
    raw_target = str(implementation_context.get("target_package_abs", "")).strip()
    if not raw_target:
        raise ValueError("implementation_context.target_package_abs 缺失")
    return Path(raw_target).resolve()


def append_repair_round(implementation_result: dict[str, Any], payload: dict[str, Any]) -> None:
    implementation_result.setdefault("repair_rounds", [])
    rounds = implementation_result["repair_rounds"]
    if isinstance(rounds, list):
        rounds.append(payload)
    else:
        implementation_result["repair_rounds"] = [payload]


def write_invalid_plan(lgwf_dir: Path, implementation_result: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    payload = {"status": "invalid_plan", "failures": failures}
    append_repair_round(implementation_result, payload)
    write_json(lgwf_dir / "implementation_result.json", implementation_result)
    return {"status": "invalid_plan", "published_files": [], "failures": failures}


def publish_repair_result(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    repair_reason = read_json(lgwf_dir / "implementation_repair_reason.json")
    repair_result = read_json(lgwf_dir / "implementation_repair_result.json")
    implementation_result = read_json(lgwf_dir / "implementation_result.json")

    if repair_reason.get("unit_output_dir") not in (None, "", STAGING_ROOT.as_posix()):
        return write_invalid_plan(
            lgwf_dir,
            implementation_result,
            [f"unit_output_dir 必须是 {STAGING_ROOT.as_posix()}"],
        )

    if repair_reason.get("repair_required") is False or repair_result.get("no_op") is True:
        append_repair_round(implementation_result, {"status": "noop", "reason": "audit already passed"})
        write_json(lgwf_dir / "implementation_result.json", implementation_result)
        return {"status": "noop", "published_files": []}

    if str(repair_result.get("status", "")).lower() == "blocked":
        risks = repair_result.get("remaining_risks", [])
        append_repair_round(implementation_result, {"status": "blocked", "remaining_risks": risks})
        write_json(lgwf_dir / "implementation_result.json", implementation_result)
        return {"status": "blocked", "published_files": [], "remaining_risks": risks}

    allowed_files, allowed_failures = target_files_from_reason(repair_reason)
    generated, generated_failures = normalize_generated_files(repair_result.get("generated_files", []))
    failures = [*allowed_failures, *generated_failures]
    if repair_reason.get("repair_required") is not True:
        failures.append("repair_required 必须是 boolean true 或 false")
    if not allowed_files and repair_reason.get("repair_required") is True:
        failures.append("repair_required=true 时 target_files 不能为空")
    if not generated and repair_reason.get("repair_required") is True:
        failures.append("repair_required=true 时 generated_files 不能为空")
    allowed = set(allowed_files)
    unexpected = [path for path in generated if path not in allowed]
    if unexpected:
        failures.append(f"repair generated files outside target_files: {unexpected}")
    if failures:
        return write_invalid_plan(lgwf_dir, implementation_result, failures)

    try:
        target_package_abs = resolve_target_package(root)
    except ValueError as exc:
        return write_invalid_plan(lgwf_dir, implementation_result, [str(exc)])

    stage_root = root / STAGING_ROOT
    missing_sources: list[str] = []
    for relative in generated:
        source = stage_root / relative
        if not source.is_file():
            missing_sources.append(f"missing staged repair file: {source}")
    if missing_sources:
        return write_invalid_plan(lgwf_dir, implementation_result, missing_sources)

    published: list[dict[str, str]] = []
    for relative in generated:
        source = stage_root / relative
        destination = target_package_abs / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")
        published.append({"path": relative})

    append_repair_round(implementation_result, {"status": "ok", "generated_files": published})
    implementation_result["generated_files"] = merge_generated_files(
        implementation_result.get("generated_files", []),
        published,
    )
    write_json(lgwf_dir / "implementation_result.json", implementation_result)
    return {"status": "ok", "published_files": published}


def main() -> None:
    result = publish_repair_result(Path.cwd())
    print(json.dumps({"lgwf_wf_create.publish_repair_result": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
