from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


STATE_KEY = "lgwf_wf_create_fast.materialize_scaffold_result"


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise TypeError(f"{path.as_posix()} 必须是 JSON object")
    return data


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def unwrap_confirmed(data: dict[str, Any]) -> dict[str, Any]:
    confirmed = data.get("confirmed")
    return confirmed if isinstance(confirmed, dict) else data


def unwrap_scaffold_plan(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("scaffold_plan"), dict):
        return data["scaffold_plan"]
    for key in (
        "lgwf_wf_create_fast.scaffold_package_result",
        "scaffold_package_result",
    ):
        wrapped = data.get(key)
        if isinstance(wrapped, dict) and isinstance(wrapped.get("scaffold_plan"), dict):
            return wrapped["scaffold_plan"]
    raise ValueError(".lgwf/scaffold_package_result.json 缺少 scaffold_plan")


def normalize_relative_path(raw_path: str, field_name: str) -> str:
    cleaned = raw_path.strip()
    if "://" in cleaned:
        raise ValueError(f"{field_name} 禁止 URL 路径")
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if candidate.is_absolute():
        raise ValueError(f"{field_name} 禁止绝对路径")
    if ":" in cleaned:
        raise ValueError(f"{field_name} 禁止盘符路径")
    if any(part == ".." for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part.lower() == ".lgwf" for part in candidate.parts):
        raise ValueError(f"{field_name} 禁止指向 `.lgwf` 运行状态目录")
    normalized = candidate.as_posix().strip("/")
    if not normalized:
        raise ValueError(f"{field_name} 不能为空")
    return normalized


def normalize_target_package_root(raw_path: str, field_name: str = "target_package_root") -> str:
    cleaned = raw_path.strip()
    if "://" in cleaned:
        raise ValueError(f"{field_name} 禁止 URL 路径")
    if not cleaned or cleaned == ".":
        raise ValueError(f"{field_name} 不能为空")
    if ":" in cleaned:
        candidate = PureWindowsPath(cleaned)
        if not candidate.is_absolute():
            raise ValueError(f"{field_name} 盘符路径必须是绝对路径")
        parts = candidate.parts
        normalized = str(candidate)
    else:
        candidate = PurePosixPath(cleaned.replace("\\", "/"))
        parts = candidate.parts
        normalized = candidate.as_posix().rstrip("/")
    if any(part == ".." for part in parts):
        raise ValueError(f"{field_name} 禁止 `..`")
    if any(part.lower() == ".lgwf" for part in parts):
        raise ValueError(f"{field_name} 禁止指向 `.lgwf` 运行状态目录")
    if not normalized:
        raise ValueError(f"{field_name} 不能为空")
    return normalized


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if isinstance(item, str) and item.strip()]


def find_workspace_root(start: Path) -> Path:
    current = start.resolve()
    candidates = [current, *current.parents]
    for candidate in candidates:
        isolation_workspace = candidate / "workspace"
        if (isolation_workspace / "workflows").is_dir() or (isolation_workspace / "vendor").is_dir():
            return isolation_workspace
    for candidate in candidates:
        if (candidate / ".git").exists():
            return candidate
    for candidate in candidates:
        if (candidate / "skills").is_dir():
            return candidate
    raise RuntimeError(f"无法从运行目录推导 workspace_root: {start}")


def ensure_within(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} 必须位于 {root.as_posix()} 内: {resolved.as_posix()}") from exc
    return resolved


def is_absolute_target(raw_path: str) -> bool:
    cleaned = raw_path.strip()
    return PureWindowsPath(cleaned).is_absolute() if ":" in cleaned else PurePosixPath(cleaned.replace("\\", "/")).is_absolute()


def resolve_target_package_root(target_package_root: str, work_dir: Path) -> Path:
    if is_absolute_target(target_package_root):
        return Path(target_package_root).resolve()
    return ensure_within(work_dir / target_package_root, work_dir, "target_package_abs")


def path_is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def protected_system_roots() -> list[Path]:
    roots: list[Path] = []
    for key in ("SystemRoot", "WINDIR", "ProgramFiles", "ProgramFiles(x86)", "ProgramData"):
        value = os.environ.get(key)
        if value:
            roots.append(Path(value))
    return roots


def assert_safe_target_abs(target_abs: Path, *, workspace_root: Path, work_dir: Path) -> None:
    resolved = target_abs.resolve()
    anchor = Path(resolved.anchor).resolve() if resolved.anchor else resolved
    if resolved == anchor:
        raise ValueError(f"target_package_root 禁止指向文件系统根目录: {resolved}")

    home = Path.home().resolve()
    exact_forbidden = {
        workspace_root.resolve(): "仓库根目录",
        work_dir.resolve(): "当前 run work dir 根目录",
        home: "用户 home 根目录",
    }
    for forbidden, label in exact_forbidden.items():
        if resolved == forbidden:
            raise ValueError(f"target_package_root 禁止指向{label}: {resolved}")

    for root in protected_system_roots():
        root_resolved = root.resolve()
        if resolved == root_resolved or path_is_relative_to(resolved, root_resolved):
            raise ValueError(f"target_package_root 禁止指向系统目录: {resolved}")


def quote_command_arg(value: Path) -> str:
    return '"' + str(value).replace('"', '\\"') + '"'


def safe_identifier(raw: str, fallback: str = "workflow") -> str:
    value = re.sub(r"[^0-9A-Za-z_]+", "_", raw.strip().replace("-", "_")).strip("_").lower()
    if not value:
        value = fallback
    if value[0].isdigit():
        value = f"wf_{value}"
    return value


def stage_dirs(scaffold_plan: dict[str, Any]) -> list[str]:
    manifest = scaffold_plan.get("stage_manifest")
    dirs: list[str] = []
    if isinstance(manifest, list):
        for item in manifest:
            if isinstance(item, dict):
                stage_dir = str(item.get("stage_dir", "")).strip()
                if stage_dir:
                    dirs.append(normalize_relative_path(stage_dir, "stage_manifest.stage_dir"))
    if dirs:
        return list(dict.fromkeys(dirs))
    found: list[str] = []
    for path in string_list(scaffold_plan.get("create_files")):
        parts = PurePosixPath(path.replace("\\", "/")).parts
        if len(parts) == 3 and parts[0] == "wf" and parts[2] == "workflow.lgwf":
            found.append(parts[1])
    return list(dict.fromkeys(found))


def stage_title(stage_dir: str) -> str:
    return stage_dir.replace("_", " ").replace("-", " ")


def render_root_workflow(scaffold_plan: dict[str, Any]) -> str:
    workflow_id = safe_identifier(str(scaffold_plan.get("workflow_name") or "generated_workflow"))
    stages = stage_dirs(scaffold_plan)
    lines = [
        f"WORKFLOW {workflow_id};",
        "ENTRY start;",
        "",
        "DEFAULTS {",
        '  ref_root workflow ".";',
        "  timeout_seconds 300;",
        f'  result_path "{workflow_id}.results.{{node}}";',
        "}",
        "",
    ]
    if not stages:
        lines.extend(
            [
                "PY start",
                '  SCRIPT "shared/scripts/run.py"',
                f"  RESULT state.{workflow_id}.start_result",
                "  CONTRACT {",
                f"    WRITE state.{workflow_id}.start_result;",
                "  };",
                "",
                "FLOW start;",
                "",
            ]
        )
        return "\n".join(lines)
    node_ids: list[str] = []
    for stage_dir in stages:
        node_id = safe_identifier(f"step_{stage_dir}", "stage")
        node_ids.append(node_id)
        lines.extend(
            [
                f"STEP {node_id}",
                f'  WORKFLOW "{stage_dir}/workflow.lgwf"',
                "  CONTRACT {",
                f"    WRITE state.{workflow_id}.{node_id}_result;",
                "  };",
                "",
            ]
        )
    lines.append("FLOW " + "\n  THEN ".join(node_ids) + ";")
    lines.append("")
    return "\n".join(lines)


def render_stage_workflow(scaffold_plan: dict[str, Any], stage_dir: str) -> str:
    workflow_id = safe_identifier(str(scaffold_plan.get("workflow_name") or "generated_workflow"))
    stage_id = safe_identifier(stage_dir, "stage")
    return "\n".join(
        [
            f"WORKFLOW {workflow_id}_{stage_id};",
            "ENTRY run_stage;",
            "",
            "DEFAULTS {",
            '  ref_root workflow ".";',
            "  timeout_seconds 300;",
            "}",
            "",
            "PY run_stage",
            '  SCRIPT "scripts/run.py"',
            f"  RESULT state.{workflow_id}.{stage_id}_result",
            "  CONTRACT {",
            f"    WRITE state.{workflow_id}.{stage_id}_result;",
            "  };",
            "",
            "FLOW run_stage;",
            "",
        ]
    )


def render_stage_run(scaffold_plan: dict[str, Any], stage_dir: str) -> str:
    workflow_name = str(scaffold_plan.get("workflow_name") or "generated-workflow")
    return f'''from __future__ import annotations

import json


def main() -> None:
    result = {{
        "status": "draft",
        "workflow_name": {json.dumps(workflow_name, ensure_ascii=False)},
        "stage": {json.dumps(stage_dir, ensure_ascii=False)},
        "message": "wf-create-fast scaffold placeholder; main agent should replace this logic.",
    }}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
'''


def render_root_agents(scaffold_plan: dict[str, Any], requirements: dict[str, Any]) -> str:
    workflow_name = str(scaffold_plan.get("workflow_name") or requirements.get("workflow_name") or "未命名 workflow")
    target_root = str(scaffold_plan.get("target_package_root") or "")
    return f"""# {workflow_name} 协作指引

## 模块定位

本目录是由 `wf-create-fast` 生成的 LGWF workflow package 初稿。当前文件结构是 scaffold，后续由主 agent 根据已确认需求和业务流继续完善。

## 入口

- Workflow：`wf/workflow.lgwf`
- Work dir：`ws`
- Target package root：`{target_root}`

## 依赖

- 依赖 LGWF runtime。
- 依赖本 package 内 `wf/` 下的 workflow、stage scripts 和 tests。

## 状态边界

- 运行状态只写入 `ws/.lgwf/`。
- 不得在 package 根目录写入 `.lgwf/`。

## 产物

- `wf/workflow.lgwf`
- `wf/artifact_contracts.json`
- 各阶段 `wf/<stage>/workflow.lgwf`
- `tests/`

## 验证

```powershell
python skills\\lgwf-wf-tools\\vendor\\lgwf-client-assist\\scripts\\lgwf.py audit {target_root}/wf/workflow.lgwf
python -m unittest discover {target_root}/tests
```

## 禁止事项

- 不要把运行状态写入 package 根目录。
- 不要保留无意义占位逻辑；主 agent 接手后应按需求补齐真实实现。
"""


def render_root_readme(scaffold_plan: dict[str, Any], requirements: dict[str, Any]) -> str:
    workflow_name = str(scaffold_plan.get("workflow_name") or requirements.get("workflow_name") or "未命名 workflow")
    target_root = str(scaffold_plan.get("target_package_root") or "")
    return f"""# {workflow_name}

本 package 由 `wf-create-fast` 生成，目前是可编辑 scaffold。主 agent 应根据已确认需求、业务流和 scaffold plan 继续完善实现。

## 入口

- `wf/workflow.lgwf`
- `ws/` 作为 LGWF work dir

## 验证

```powershell
python skills\\lgwf-wf-tools\\vendor\\lgwf-client-assist\\scripts\\lgwf.py audit {target_root}/wf/workflow.lgwf
python -m unittest discover {target_root}/tests
```

## 当前状态

当前文件是最小 scaffold，不代表最终业务实现已经完成。
"""


def render_entry_contract(scaffold_plan: dict[str, Any]) -> str:
    target_root = str(scaffold_plan.get("target_package_root") or "")
    workflow_name = str(scaffold_plan.get("workflow_name") or "generated-workflow")
    payload = {
        "id": workflow_name,
        "kind": "lgwf",
        "version": 1,
        "workflow_lgwf": f"{target_root}/wf/workflow.lgwf",
        "work_dir": f"{target_root}/ws",
        "input_mode": "input_json_required",
        "input_schema": {
            "type": "object",
            "properties": {
                "request": {"type": "object"}
            }
        },
        "auto_human_policy": "conditional",
        "outputs": {}
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_skill(scaffold_plan: dict[str, Any]) -> str:
    workflow_name = str(scaffold_plan.get("workflow_name") or "generated-workflow")
    return f"""---
name: {workflow_name}
description: 由 wf-create-fast 生成的 LGWF workflow skill facade。
---

# {workflow_name}

本 `SKILL.md` 只作为入口说明和路由封装。内部 workflow 位于 `wf/workflow.lgwf`，运行状态写入 `ws/.lgwf/`。
"""


def render_root_artifact_contracts(scaffold_plan: dict[str, Any]) -> str:
    payload = {
        "workflow_id": scaffold_plan.get("workflow_name", "generated-workflow"),
        "runtime_artifacts": [],
        "target_artifacts": string_list(scaffold_plan.get("create_files")),
        "notes": ["由 wf-create-fast materialize_scaffold 生成的初始 artifact contract。"]
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_stage_artifact_contracts(stage_dir: str) -> str:
    payload = {
        "stage": stage_dir,
        "runtime_artifacts": [],
        "outputs": [f"state.<workflow>.{safe_identifier(stage_dir)}_result"],
        "notes": ["由 wf-create-fast 生成的阶段初始 artifact contract。"]
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_stage_prompt(stage_dir: str) -> str:
    return f"""# {stage_title(stage_dir)}

当前 prompt 是 `wf-create-fast` 生成的 scaffold 占位。主 agent 接手后应根据已确认需求和业务流替换为真实阶段说明。
"""


def render_stage_resource_readme(stage_dir: str) -> str:
    return f"""# {stage_title(stage_dir)} resources

本目录用于存放 `{stage_dir}` 阶段的模板、schema、示例和只读资料。当前内容由 `wf-create-fast` 生成，后续由主 agent 完善。
"""


def render_test_file(scaffold_plan: dict[str, Any]) -> str:
    stages = stage_dirs(scaffold_plan)
    stage_assertions = "\n".join(
        f'        self.assertTrue((root / "wf" / {stage!r} / "workflow.lgwf").is_file())' for stage in stages
    )
    return f'''from __future__ import annotations

import unittest
from pathlib import Path


class WorkflowStructureTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "AGENTS.md").is_file())
        self.assertTrue((root / "README.md").is_file())
        self.assertTrue((root / "entry_contract.json").is_file())
        self.assertTrue((root / "wf" / "workflow.lgwf").is_file())
{stage_assertions if stage_assertions else "        self.assertTrue((root / \"wf\").is_dir())"}

    def test_no_runtime_state_in_package_root(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / ".lgwf").exists())


if __name__ == "__main__":
    unittest.main()
'''


def default_file_content(
    package_path: str,
    scaffold_plan: dict[str, Any],
    requirements: dict[str, Any],
) -> str:
    if package_path == "AGENTS.md":
        return render_root_agents(scaffold_plan, requirements)
    if package_path == "README.md":
        return render_root_readme(scaffold_plan, requirements)
    if package_path == "entry_contract.json":
        return render_entry_contract(scaffold_plan)
    if package_path == "SKILL.md":
        return render_skill(scaffold_plan)
    if package_path == "wf/workflow.lgwf":
        return render_root_workflow(scaffold_plan)
    if package_path == "wf/artifact_contracts.json":
        return render_root_artifact_contracts(scaffold_plan)
    if package_path.startswith("tests/") and package_path.endswith(".py"):
        return render_test_file(scaffold_plan)
    if package_path == "tests/README.md":
        return "# tests\n\n本目录包含目标 workflow 的最小结构测试。后续由主 agent 补齐业务测试。\n"

    parts = PurePosixPath(package_path).parts
    if len(parts) >= 3 and parts[0] == "wf":
        stage_dir = parts[1]
        tail = "/".join(parts[2:])
        if tail == "workflow.lgwf":
            return render_stage_workflow(scaffold_plan, stage_dir)
        if tail == "artifact_contracts.json":
            return render_stage_artifact_contracts(stage_dir)
        if tail == "scripts/run.py":
            return render_stage_run(scaffold_plan, stage_dir)
        if tail == "agents/prompt.md":
            return render_stage_prompt(stage_dir)
        if tail == "resources/README.md":
            return render_stage_resource_readme(stage_dir)

    return f"# {package_path}\n\n由 `wf-create-fast` 生成的 scaffold 文件。主 agent 接手后应按需求完善。\n"


def materialize_scaffold(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    requirements = unwrap_confirmed(read_json(lgwf_dir / "create_requirements.json"))
    business_flow = unwrap_confirmed(read_json(lgwf_dir / "business_flow.json"))
    scaffold_plan = unwrap_scaffold_plan(read_json(lgwf_dir / "scaffold_package_result.json"))

    target_package_root = normalize_target_package_root(str(scaffold_plan.get("target_package_root", "")), "target_package_root")
    workspace_root = find_workspace_root(root)
    target_abs = resolve_target_package_root(target_package_root, root.resolve())
    assert_safe_target_abs(target_abs, workspace_root=workspace_root, work_dir=root.resolve())
    target_abs.mkdir(parents=True, exist_ok=True)

    create_dirs = [normalize_relative_path(path, "create_dirs") for path in string_list(scaffold_plan.get("create_dirs"))]
    create_files = [normalize_relative_path(path, "create_files") for path in string_list(scaffold_plan.get("create_files"))]

    created_dirs: list[str] = []
    for rel_dir in create_dirs:
        directory = ensure_within(target_abs / rel_dir, target_abs, f"create_dirs.{rel_dir}")
        directory.mkdir(parents=True, exist_ok=True)
        created_dirs.append(rel_dir)

    created_files: list[str] = []
    skipped_existing_files: list[str] = []
    for rel_file in create_files:
        file_path = ensure_within(target_abs / rel_file, target_abs, f"create_files.{rel_file}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if file_path.exists() and file_path.read_text(encoding="utf-8-sig").strip():
            skipped_existing_files.append(rel_file)
            continue
        file_path.write_text(default_file_content(rel_file, scaffold_plan, requirements), encoding="utf-8")
        created_files.append(rel_file)

    validation_commands = [
        "python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py "
        f"audit {quote_command_arg(target_abs / 'wf' / 'workflow.lgwf')}",
        f"python -m unittest discover {quote_command_arg(target_abs / 'tests')}",
    ]
    result = {
        "status": "partial_existing_files" if skipped_existing_files else "ok",
        "workflow_name": scaffold_plan.get("workflow_name", ""),
        "target_package_root": target_package_root,
        "target_package_abs": str(target_abs),
        "workspace_root": str(workspace_root.resolve()),
        "created_dirs": created_dirs,
        "created_files": created_files,
        "skipped_existing_files": skipped_existing_files,
        "validation_commands": validation_commands,
        "handoff_ready": True,
        "business_flow_stage_count": len(business_flow.get("stages", [])) if isinstance(business_flow.get("stages"), list) else 0,
    }
    write_json(lgwf_dir / "materialize_scaffold_result.json", result)
    return result


def main() -> None:
    result = materialize_scaffold(Path.cwd())
    print(json.dumps({STATE_KEY: result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
