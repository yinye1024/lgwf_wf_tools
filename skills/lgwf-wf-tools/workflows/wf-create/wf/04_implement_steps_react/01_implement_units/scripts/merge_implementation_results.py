"""合并 FOREACH implementation unit 结果为原 implementation_result 契约。"""

from __future__ import annotations

import json
import sys
from pathlib import Path, PurePosixPath
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_payload() -> Any:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def strip_target_package_root(path_value: str, target_package_root: str) -> str:
    normalized = path_value.strip().replace("\\", "/")
    if target_package_root:
        root = target_package_root.strip().replace("\\", "/").strip("/")
        prefix = f"{root}/"
        if normalized == root:
            return "."
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return normalized


def normalize_package_path(raw_path: str, target_package_root: str, target_abs: str) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
    if target_abs:
        target_prefix = target_abs.replace("\\", "/").rstrip("/") + "/"
        if cleaned.startswith(target_prefix):
            cleaned = cleaned[len(target_prefix) :]
    cleaned = strip_target_package_root(cleaned, target_package_root)
    path = PurePosixPath(cleaned)
    if not cleaned or path.is_absolute() or ":" in cleaned:
        raise ValueError(f"非法生成文件路径: {raw_path}")
    if any(part in {"..", ".lgwf"} for part in path.parts):
        raise ValueError(f"非法生成文件路径: {raw_path}")
    return path.as_posix().strip("/")


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def extract_unit_results(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in (
        "items",
        "unit_results",
        "implementation_unit_results",
        "results",
        "lgwf_wf_create.implementation_unit_results",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def unwrap_result(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    for key in (
        "lgwf_wf_create.current_implementation_unit_result",
        "current_implementation_unit_result",
        "output",
        "result",
        "value",
    ):
        value = item.get(key)
        if isinstance(value, dict):
            result = dict(value)
            inherit_foreach_metadata(result, item)
            return result
    result = dict(item)
    inherit_foreach_metadata(result, item)
    if str(result.get("status", "")).lower() == "failed":
        message = str(result.get("message", "")).strip()
        if message and not isinstance(result.get("remaining_risks"), list):
            result["remaining_risks"] = [message]
    return result


def inherit_foreach_metadata(result: dict[str, Any], wrapper: dict[str, Any]) -> None:
    item = wrapper.get("item")
    if "foreach_index" not in result and isinstance(wrapper.get("index"), int):
        result["foreach_index"] = wrapper["index"]
    if "unit_id" in result or not isinstance(item, dict):
        return
    unit_id = str(item.get("unit_id", "")).strip()
    if unit_id:
        result["unit_id"] = unit_id


def generated_file_paths(result: dict[str, Any], target_package_root: str, target_abs: str) -> list[str]:
    paths: list[str] = []
    raw_items = result.get("generated_files", [])
    if isinstance(raw_items, list):
        for item in raw_items:
            if isinstance(item, dict):
                raw_path = str(item.get("path", "")).strip()
            else:
                raw_path = str(item).strip()
            if raw_path:
                paths.append(normalize_package_path(raw_path, target_package_root, target_abs))
    generated = result.get("generated", {})
    if isinstance(generated, dict):
        root_files = generated.get("root_files", [])
        if isinstance(root_files, list):
            for item in root_files:
                raw_path = str(item).strip()
                if raw_path:
                    paths.append(normalize_package_path(raw_path, target_package_root, target_abs))
        by_step = generated.get("by_step", [])
        if isinstance(by_step, list):
            for step in by_step:
                if not isinstance(step, dict):
                    continue
                step_files = step.get("generated_files", [])
                if not isinstance(step_files, list):
                    continue
                for item in step_files:
                    raw_path = str(item).strip()
                    if raw_path:
                        paths.append(normalize_package_path(raw_path, target_package_root, target_abs))
    return unique(paths)


def merge_generated_summary(results: list[dict[str, Any]], target_package_root: str, target_abs: str) -> dict[str, Any]:
    root_files: list[str] = []
    by_step: list[dict[str, Any]] = []
    for result in results:
        generated = result.get("generated", {})
        if not isinstance(generated, dict):
            continue
        raw_root_files = generated.get("root_files", [])
        if isinstance(raw_root_files, list):
            for item in raw_root_files:
                raw_path = str(item).strip()
                if raw_path:
                    root_files.append(normalize_package_path(raw_path, target_package_root, target_abs))
        raw_by_step = generated.get("by_step", [])
        if isinstance(raw_by_step, list):
            for item in raw_by_step:
                if not isinstance(item, dict):
                    continue
                copied = dict(item)
                step_files = copied.get("generated_files", [])
                if isinstance(step_files, list):
                    copied["generated_files"] = [
                        normalize_package_path(str(path), target_package_root, target_abs)
                        for path in step_files
                        if str(path).strip()
                    ]
                by_step.append(copied)
    return {"root_files": unique(root_files), "by_step": by_step}


def result_status(results: list[dict[str, Any]]) -> str:
    if not results:
        return "failed"
    statuses = {str(result.get("status", "")).lower() for result in results}
    if any(status in {"failed", "error"} for status in statuses):
        return "failed"
    if any(status in {"partial", "needs_review"} for status in statuses):
        return "partial"
    return "ok"


def merge_implementation_results(root: Path, payload: Any) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    context = load_json(lgwf_dir / "implementation_context.json")
    units_payload = load_json(lgwf_dir / "implementation_units.json")
    raw_results = extract_unit_results(payload)
    results = [unwrap_result(item) for item in raw_results]
    results = [item for item in results if item]
    target_package_root = str(context.get("target_package_root", "")).strip()
    target_abs = str(context.get("target_package_abs", "")).strip()
    workflow_name = str(context.get("workflow_name", "")).strip()
    generated_paths = unique(
        [
            path
            for result in results
            for path in generated_file_paths(result, target_package_root, target_abs)
        ]
    )
    generated = merge_generated_summary(results, target_package_root, target_abs)
    failed_units = [
        str(result.get("unit_id", ""))
        for result in results
        if str(result.get("status", "")).lower() in {"failed", "error"}
    ]
    remaining_risks = [
        str(risk)
        for result in results
        for risk in result.get("remaining_risks", [])
        if isinstance(result.get("remaining_risks", []), list) and str(risk).strip()
    ]
    validation: list[dict[str, Any]] = []
    for result in results:
        raw_validation = result.get("validation") or result.get("verification")
        if isinstance(raw_validation, list):
            validation.extend(item for item in raw_validation if isinstance(item, dict))
    merged = {
        "status": result_status(results),
        "workflow_name": workflow_name,
        "target_package_root": target_package_root,
        "target_package_abs": target_abs,
        "generated_files": [{"path": path} for path in generated_paths],
        "generated": generated,
        "unit_count": len(results),
        "unit_results": results,
        "failed_units": [unit for unit in failed_units if unit],
        "remaining_risks": remaining_risks,
        "selection_mode": units_payload.get("selection_mode", ""),
        "implementation_units": units_payload.get("implementation_units", []),
    }
    if validation:
        merged["validation"] = validation
        merged["verification"] = validation
    write_json(lgwf_dir / "implementation_result.json", merged)
    return merged


def main() -> None:
    result = merge_implementation_results(Path.cwd(), read_payload())
    print(
        json.dumps(
            {
                "lgwf_wf_create.merge_implementation_results_result": result,
                "lgwf_wf_create.implementation_result": result,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
