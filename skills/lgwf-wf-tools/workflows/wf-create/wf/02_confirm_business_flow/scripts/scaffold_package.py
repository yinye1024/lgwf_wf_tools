"""`scaffold_package` 的确定性脚手架规则。

当前阶段的目标是把已确认需求和业务流转映射成“将要创建什么”的稳定计划，
同时锁定相对路径、目录边界和 work dir 约束。脚手架只负责目标 package 框架，
不向目标 package 根目录写入 `.lgwf` 运行状态；运行状态边界仍归 `ws/.lgwf`。
"""

from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path, PurePosixPath
from typing import Any


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "resources" / "scaffold_package_template.json"
VALIDATOR_PATH = Path(__file__).resolve().parents[2] / "shared" / "scripts" / "validate_two_layer_workflow.py"

DEFAULT_REQUEST = {
    "workflow_name": "lgwf-wf-create-example",
    "target_package_root": "skills/example-workflow",
    "package_profile": "internal_workflow_package",
    "business_flow": {
        "stages": [
            {
                "stage_id": "package_scaffold",
                "key_nodes": ["scaffold_package"],
                "human_approval": False,
            }
        ]
    },
}


def load_scaffold_template() -> dict[str, Any]:
    """读取脚手架模板资源，保持目录结构规则集中维护。"""

    data = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("scaffold_package_template.json 必须是 JSON object")
    return data


def require_string_list(value: Any, key: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{key} 必须是字符串数组")
    return value


def select_template_profile(template: dict[str, Any], raw_profile: Any) -> tuple[str, dict[str, Any]]:
    profiles = template.get("profiles", {})
    if not isinstance(profiles, dict):
        raise TypeError("template.profiles 必须是 JSON object")
    default_profile = str(template.get("default_profile", "internal_workflow_package"))
    package_profile = str(raw_profile or default_profile).strip() or default_profile
    if package_profile not in profiles:
        raise ValueError(f"未知 package_profile: {package_profile}")
    profile = profiles[package_profile]
    if not isinstance(profile, dict):
        raise TypeError(f"profile {package_profile} 必须是 JSON object")
    return package_profile, profile


def normalize_relative_path(raw_path: str) -> str:
    """只允许包内相对路径，禁止绝对路径、盘符路径和 `..`。"""

    cleaned = raw_path.strip()
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError("target_package_root 不能为空")
    if candidate.is_absolute():
        raise ValueError("target_package_root 只使用相对路径，禁止绝对路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError("target_package_root 禁止 `..`")
    if ":" in cleaned:
        raise ValueError("target_package_root 禁止盘符路径")
    if any(part == ".lgwf" for part in candidate.parts):
        raise ValueError("target_package_root 禁止指向 `.lgwf` 运行状态目录")
    normalized = candidate.as_posix().strip("/")
    if not normalized:
        raise ValueError("target_package_root 不能为空")
    return normalized


def validate_plan_paths(plan: dict[str, Any]) -> bool:
    """校验脚手架计划内的文件和目录路径仍满足包内相对路径规则。"""

    for key in ("create_dirs", "create_files"):
        for raw_path in plan.get(key, []):
            path = normalize_relative_path(str(raw_path))
            if path.startswith(".lgwf/"):
                raise ValueError(f"{key} 禁止写入目标 package 根目录 `.lgwf`")
    validator = load_structure_validator()
    structure_errors = validator.validate_scaffold_paths(
        [*plan.get("create_dirs", []), *plan.get("create_files", [])]
    )
    if structure_errors:
        raise ValueError("脚手架结构不满足两层 workflow 规则: " + "; ".join(structure_errors))
    return True


def load_structure_validator():
    spec = importlib.util.spec_from_file_location("validate_two_layer_workflow", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_scaffold_plan(request: dict[str, Any]) -> dict[str, Any]:
    """根据确认后的输入生成确定性脚手架计划。"""

    template = load_scaffold_template()
    package_profile, profile = select_template_profile(template, request.get("package_profile"))
    target_package_root = normalize_relative_path(str(request["target_package_root"]))
    workflow_name = str(request.get("workflow_name", "")).strip()
    business_flow = request.get("business_flow", {})
    stages = business_flow.get("stages", [])
    step_dirs = require_string_list(template.get("step_dirs", []), "template.step_dirs")
    step_private_dirs = require_string_list(template.get("step_private_dirs", []), "template.step_private_dirs")

    plan = {
        "workflow_name": workflow_name or "unnamed-workflow",
        "target_package_root": target_package_root,
        "package_profile": package_profile,
        "template": {
            "template_id": template.get("template_id", "workflow_packaged_skill"),
            "template_version": template.get("template_version", 1),
            "description": template.get("description", ""),
            "profile_description": profile.get("description", ""),
        },
        "rules": {
            "path_policy": [
                "只使用相对路径",
                "禁止绝对路径",
                "禁止 `..`",
            ],
            "state_boundary": [
                "脚手架只创建目标 package 框架",
                "不向目标 package 根目录写入 `.lgwf`",
                "运行状态边界仍归 `ws/.lgwf`",
            ],
        },
        "create_dirs": [
            *require_string_list(template.get("root_dirs", []), "template.root_dirs"),
            *[f"wf/{step_dir}" for step_dir in step_dirs],
            *[f"wf/{step_dir}/{private_dir}" for step_dir in step_dirs for private_dir in step_private_dirs],
        ],
        "create_files": [
            *require_string_list(profile.get("root_files", []), f"template.profiles.{package_profile}.root_files"),
            *[f"wf/{step_dir}/workflow.lgwf" for step_dir in step_dirs],
            *require_string_list(template.get("workflow_files", []), "template.workflow_files"),
            "wf/shared/scripts/review_context.py",
            *require_string_list(template.get("test_files", []), "template.test_files"),
        ],
        "placeholders": template.get("placeholders", {}),
        "derived_from_business_flow": [
            {
                "stage_id": stage.get("stage_id", ""),
                "key_nodes": stage.get("key_nodes", []),
                "human_approval": bool(stage.get("human_approval", False)),
            }
            for stage in stages
        ],
    }
    validate_plan_paths(plan)
    return plan


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def build_scaffold_plan_from_root(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    requirements = load_json(lgwf_dir / "create_requirements.json").get("confirmed", {})
    business_flow = load_json(lgwf_dir / "business_flow.json").get("confirmed", {})
    if not requirements and not business_flow:
        return build_scaffold_plan(DEFAULT_REQUEST)
    request = {
        "workflow_name": requirements.get("workflow_name", business_flow.get("workflow_name", "")),
        "target_package_root": requirements.get("target_package_root", business_flow.get("target_package_root", "")),
        "package_profile": requirements.get("package_profile", business_flow.get("package_profile", "")),
        "business_flow": business_flow,
    }
    return build_scaffold_plan(request)


def main() -> None:
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        request = json.loads(raw) if raw else None
    else:
        request = None
    scaffold_plan = build_scaffold_plan_from_root(Path.cwd()) if request is None else build_scaffold_plan(request)
    result = {"lgwf_wf_create.scaffold_package_result": {"scaffold_plan": scaffold_plan}}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
