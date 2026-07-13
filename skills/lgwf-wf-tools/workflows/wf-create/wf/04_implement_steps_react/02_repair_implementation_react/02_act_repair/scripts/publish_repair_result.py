"""发布修复 ACT 的 staging 文件，并更新 implementation_result。"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_package_path(raw_path: str) -> str:
    cleaned = str(raw_path).strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned or cleaned == ".":
        raise ValueError("generated repair file 不能为空")
    if path.is_absolute() or ":" in cleaned or any(part == ".." for part in path.parts):
        raise ValueError(f"generated repair file 必须是 package-relative path: {raw_path}")
    if path.parts and path.parts[0] == ".lgwf":
        raise ValueError(f"generated repair file 不得写入 .lgwf: {raw_path}")
    return path.as_posix()


def normalize_generated_files(raw_files: Any) -> list[str]:
    if not isinstance(raw_files, list):
        return []
    result: list[str] = []
    for item in raw_files:
        if isinstance(item, dict):
            raw_path = item.get("path", "")
        else:
            raw_path = item
        path = normalize_package_path(str(raw_path))
        if path not in result:
            result.append(path)
    return result


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


def publish_repair_result(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    context = read_json(lgwf_dir / "implementation_repair_context.json")
    repair_result = read_json(lgwf_dir / "implementation_repair_result.json")
    implementation_result = read_json(lgwf_dir / "implementation_result.json")
    implementation_result.setdefault("repair_rounds", [])

    if context.get("repair_required") is False or repair_result.get("no_op") is True:
        implementation_result["repair_rounds"].append({"status": "noop", "reason": "audit already passed"})
        write_json(lgwf_dir / "implementation_result.json", implementation_result)
        return {"status": "noop", "published_files": []}

    if str(repair_result.get("status", "")).lower() == "blocked":
        risks = repair_result.get("remaining_risks", [])
        implementation_result["repair_rounds"].append({"status": "blocked", "remaining_risks": risks})
        write_json(lgwf_dir / "implementation_result.json", implementation_result)
        return {"status": "blocked", "published_files": [], "remaining_risks": risks}

    allowed = {normalize_package_path(str(path)) for path in context.get("target_files", []) if str(path).strip()}
    generated = normalize_generated_files(repair_result.get("generated_files", []))
    unexpected = [path for path in generated if path not in allowed]
    if unexpected:
        raise ValueError(f"repair generated files outside target_files: {unexpected}")

    target_package_abs = resolve_target_package(root)
    stage_root = root / str(context.get("unit_output_dir") or ".lgwf/implementation_repair_stage")
    published: list[dict[str, str]] = []
    for relative in generated:
        source = stage_root / relative
        destination = target_package_abs / relative
        if not source.is_file():
            raise FileNotFoundError(f"missing staged repair file: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8-sig"), encoding="utf-8")
        published.append({"path": relative})

    implementation_result["repair_rounds"].append({"status": "ok", "generated_files": published})
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
