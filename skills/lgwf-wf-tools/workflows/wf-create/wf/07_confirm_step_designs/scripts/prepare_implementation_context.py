"""为实现阶段生成确定性的路径上下文。"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def normalize_relative_path(raw_path: str, field_name: str) -> str:
    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if candidate.is_absolute():
        raise ValueError(f"{field_name} 禁止绝对路径")
    if ":" in cleaned:
        raise ValueError(f"{field_name} 禁止盘符路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part == ".lgwf" for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止指向 `.lgwf` 运行状态目录")
    normalized = candidate.as_posix().strip("/")
    if not normalized:
        raise ValueError(f"{field_name} 不能为空")
    return normalized


def find_workspace_root(start: Path) -> Path:
    current = start.resolve()
    candidates = [current, *current.parents]
    for candidate in candidates:
        if (candidate / ".git").exists():
            return candidate
    for candidate in candidates:
        if (candidate / "skills").is_dir():
            return candidate
    raise RuntimeError(f"无法从运行目录推导仓库根目录: {start}")


def load_confirmed_target(lgwf_dir: Path) -> dict[str, Any]:
    implementation = load_json(lgwf_dir / "implementation_context.json")
    requirements = load_json(lgwf_dir / "create_requirements.json").get("confirmed", {})
    business_flow = load_json(lgwf_dir / "business_flow.json").get("confirmed", {})
    scaffold = load_json(lgwf_dir / "scaffold_package_result.json").get("scaffold_plan", {})
    sources = [implementation, scaffold, requirements, business_flow]
    target_package_root = next(
        (source.get("target_package_root") for source in sources if isinstance(source.get("target_package_root"), str)),
        "",
    )
    workflow_name = next(
        (source.get("workflow_name") for source in sources if isinstance(source.get("workflow_name"), str)),
        "",
    )
    package_profile = next(
        (source.get("package_profile") for source in sources if isinstance(source.get("package_profile"), str)),
        "internal_workflow_package",
    )
    return {
        "workflow_name": workflow_name or "unnamed-workflow",
        "target_package_root": normalize_relative_path(str(target_package_root), "target_package_root"),
        "package_profile": package_profile or "internal_workflow_package",
    }


def build_implementation_context(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    target = load_confirmed_target(lgwf_dir)
    workspace_root = find_workspace_root(root)
    target_abs = (workspace_root / target["target_package_root"]).resolve()
    try:
        target_abs.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError("target_package_abs 必须位于 workspace_root 内") from exc
    context = {
        "workflow_name": target["workflow_name"],
        "target_package_root": target["target_package_root"],
        "target_package_abs": str(target_abs),
        "workspace_root": str(workspace_root),
        "work_dir": str(root.resolve()),
        "package_profile": target["package_profile"],
        "path_contract": {
            "target_package_root_semantics": "workspace_root 相对路径",
            "implementation_rule": "读写目标包时必须使用 target_package_abs，禁止从 work_dir 通过 .. 猜测仓库根",
            "runtime_state_rule": "运行产物只写入 work_dir/.lgwf 或 work_dir/reports",
        },
    }
    (lgwf_dir / "implementation_context.json").write_text(
        json.dumps(context, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return context


def main() -> None:
    context = build_implementation_context(Path.cwd())
    print(json.dumps({"lgwf_wf_create.implementation_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
