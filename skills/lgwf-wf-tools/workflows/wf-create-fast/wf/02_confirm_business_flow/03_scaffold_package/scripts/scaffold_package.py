"""`scaffold_package` 的确定性脚手架规则。

当前阶段的目标是把已确认需求和业务流转映射成“将要创建什么”的稳定计划，
同时锁定相对路径、目录边界和 work dir 约束。脚手架只负责目标 package 框架，
不向目标 package 根目录写入 `.lgwf` 运行状态；运行状态边界仍归 `ws/.lgwf`。
"""

from __future__ import annotations

import json
import importlib.util
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "resources" / "scaffold_package_template.json"
VALIDATOR_PATH = Path(__file__).resolve().parents[3] / "shared" / "scripts" / "validate_two_layer_workflow.py"
ROOT_PACKAGE_FILES = {"SKILL.md", "AGENTS.md", "README.md", "entry_contract.json"}
PACKAGE_FILE_PATTERN = re.compile(r"[\w./-]+\.(?:md|py|json|lgwf)")

DEFAULT_REQUEST = {
    "workflow_name": "lgwf-wf-create-fast-example",
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


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(flatten_text(child) for child in value.values())
    if isinstance(value, list):
        return "\n".join(flatten_text(child) for child in value)
    return str(value) if value is not None else ""


def semantic_required_package_files(*sources: dict[str, Any]) -> list[str]:
    """从已确认需求/业务流文本中提取目标 package 的显式文件要求。"""

    blob = "\n".join(flatten_text(source) for source in sources if isinstance(source, dict))
    files: list[str] = []
    for match in PACKAGE_FILE_PATTERN.findall(blob.replace("\\", "/")):
        candidate = match.strip("`'\"“”‘’，,。；;：:（）()[]{}<>")
        if not candidate:
            continue
        try:
            path = normalize_relative_path(candidate)
        except ValueError:
            continue
        parts = PurePosixPath(path).parts
        if not parts:
            continue
        if parts[0] in {".lgwf", "ws"}:
            continue
        if path in ROOT_PACKAGE_FILES or parts[0] in {"scripts", "tests", "wf"}:
            files.append(path)
    return unique(files)


def infer_package_profile(
    template: dict[str, Any],
    raw_profile: Any,
    target_package_root: str,
    semantic_files: list[str],
    *sources: dict[str, Any],
) -> str:
    if isinstance(raw_profile, str) and raw_profile.strip():
        return raw_profile.strip()
    profiles = template.get("profiles", {})
    default_profile = str(template.get("default_profile", "internal_workflow_package"))
    text_blob = "\n".join(flatten_text(source) for source in sources if isinstance(source, dict)).lower()
    looks_like_skill = (
        "SKILL.md" in semantic_files
        or "codex skill" in text_blob
        or "skill_wrapped_workflow" in text_blob
        or "外层模块：codex_skill" in text_blob
    )
    if looks_like_skill and isinstance(profiles, dict) and "skill_wrapped_workflow" in profiles:
        return "skill_wrapped_workflow"
    return default_profile


def slugify_id(raw_value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", raw_value.strip()).strip("_")
    return cleaned or fallback


def strip_numeric_prefix(stage_id: str) -> str:
    return re.sub(r"^\d+[_-]+", "", stage_id).strip("_-")


def numbered_stage_dir(index: int, stage_id: str) -> str:
    suffix = strip_numeric_prefix(stage_id) or f"stage_{index:02d}"
    return f"{index:02d}_{suffix}"


def build_stage_manifest(stages: Any, fallback_step_dirs: list[str]) -> list[dict[str, Any]]:
    source_items: list[dict[str, Any]] = []
    if isinstance(stages, list):
        source_items = [item for item in stages if isinstance(item, dict)]
    if not source_items:
        source_items = [{"stage_id": strip_numeric_prefix(step_dir)} for step_dir in fallback_step_dirs]

    manifest: list[dict[str, Any]] = []
    used_dirs: set[str] = set()
    for index, stage in enumerate(source_items, start=1):
        raw_stage_id = str(stage.get("stage_id") or stage.get("id") or stage.get("name") or "").strip()
        stage_id = slugify_id(strip_numeric_prefix(raw_stage_id), f"stage_{index:02d}")
        stage_dir = numbered_stage_dir(index, stage_id)
        if stage_dir in used_dirs:
            stage_dir = f"{stage_dir}_{index:02d}"
        used_dirs.add(stage_dir)
        manifest.append(
            {
                "stage_id": stage_id,
                "stage_dir": stage_dir,
                "workflow_ref": f"wf/{stage_dir}/workflow.lgwf",
                "key_nodes": stage.get("key_nodes", []),
                "human_approval": bool(stage.get("human_approval", False)),
            }
        )
    return manifest


def stage_dirs_from_manifest(stage_manifest: list[dict[str, Any]]) -> list[str]:
    return unique([str(item.get("stage_dir", "")).strip() for item in stage_manifest])


def profile_string_list(
    profile: dict[str, Any],
    template: dict[str, Any],
    key: str,
    *,
    template_key: str | None = None,
) -> list[str]:
    if key in profile:
        return require_string_list(profile.get(key, []), f"profile.{key}")
    fallback_key = template_key or key
    return require_string_list(template.get(fallback_key, []), f"template.{fallback_key}")


def stage_scaffold_files(stage_dirs: list[str], stage_private_dirs: list[str]) -> list[str]:
    files: list[str] = []
    for stage_dir in stage_dirs:
        files.append(f"wf/{stage_dir}/workflow.lgwf")
        files.append(f"wf/{stage_dir}/artifact_contracts.json")
        if "agents" in stage_private_dirs:
            files.append(f"wf/{stage_dir}/agents/prompt.md")
        if "scripts" in stage_private_dirs:
            files.append(f"wf/{stage_dir}/scripts/run.py")
        if "resources" in stage_private_dirs:
            files.append(f"wf/{stage_dir}/resources/README.md")
    return files


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
        raise ValueError("脚手架结构不满足模块化 workflow 结构规则: " + "; ".join(structure_errors))
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
    target_package_root = normalize_relative_path(str(request["target_package_root"]))
    business_flow = request.get("business_flow", {})
    semantic_files = semantic_required_package_files(request, business_flow)
    package_profile, profile = select_template_profile(
        template,
        infer_package_profile(
            template,
            request.get("package_profile"),
            target_package_root,
            semantic_files,
            request,
            business_flow if isinstance(business_flow, dict) else {},
        ),
    )
    workflow_name = str(request.get("workflow_name", "")).strip()
    stages = business_flow.get("stages", [])
    step_dirs = require_string_list(template.get("step_dirs", []), "template.step_dirs")
    step_private_dirs = profile_string_list(profile, template, "stage_private_dirs", template_key="step_private_dirs")
    stage_manifest = build_stage_manifest(stages, step_dirs)
    stage_dirs = stage_dirs_from_manifest(stage_manifest)

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
        "stage_manifest": stage_manifest,
        "create_dirs": unique(
            [
            *require_string_list(template.get("root_dirs", []), "template.root_dirs"),
            *[f"wf/{stage_dir}" for stage_dir in stage_dirs],
            *[f"wf/{stage_dir}/{private_dir}" for stage_dir in stage_dirs for private_dir in step_private_dirs],
            ]
        ),
        "create_files": unique(
            [
            *require_string_list(profile.get("root_files", []), f"template.profiles.{package_profile}.root_files"),
            "entry_contract.json",
            *require_string_list(template.get("workflow_files", []), "template.workflow_files"),
            *stage_scaffold_files(stage_dirs, step_private_dirs),
            *require_string_list(template.get("test_files", []), "template.test_files"),
            *semantic_files,
            ]
        ),
        "placeholders": template.get("placeholders", {}),
        "derived_from_business_flow": [
            {
                "stage_id": stage.get("stage_id", ""),
                "stage_dir": stage_manifest[index]["stage_dir"] if index < len(stage_manifest) else "",
                "key_nodes": stage.get("key_nodes", []),
                "human_approval": bool(stage.get("human_approval", False)),
            }
            for index, stage in enumerate(stages if isinstance(stages, list) else [])
            if isinstance(stage, dict)
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
        "purpose": requirements.get("purpose", business_flow.get("business_goal", "")),
        "expected_outputs": requirements.get("expected_outputs", []),
        "package_source_files": requirements.get("package_source_files", []),
        "proposal_notes": requirements.get("proposal_notes", []),
        "business_flow": business_flow,
    }
    return build_scaffold_plan(request)


def main() -> None:
    root = Path.cwd()
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        request = json.loads(raw) if raw else None
    else:
        request = None
    scaffold_plan = build_scaffold_plan_from_root(root) if request is None else build_scaffold_plan(request)
    state_value = {"scaffold_plan": scaffold_plan}
    output_path = root / ".lgwf" / "scaffold_package_result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(state_value, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {"lgwf_wf_create_fast.scaffold_package_result": state_value}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
