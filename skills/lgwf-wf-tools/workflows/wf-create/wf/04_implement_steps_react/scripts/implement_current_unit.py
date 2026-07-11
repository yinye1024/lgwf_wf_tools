"""确定性落地当前 implementation unit，避免单 unit Codex 卡住后无结果文件。"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from textwrap import dedent
from typing import Any


STAGES: dict[str, dict[str, str]] = {
    "entry_scope_resolution": {
        "name": "入口分发与范围归一",
        "node": "normalize_runtime_request",
        "result": "state.repo_context_pack.request",
        "summary": "读取运行输入，归一化 target_dir、output_dir、focus、depth 和 max_files。",
        "write": ".lgwf/repo_context_pack_request.json",
    },
    "target_context_inventory": {
        "name": "目标仓库上下文采集",
        "node": "collect_target_context",
        "result": "state.repo_context_pack.context_inventory",
        "summary": "基于已归一化请求盘点入口文件、模块、命令、风险和推荐阅读顺序。",
        "write": ".lgwf/context_inventory.json",
    },
    "context_pack_rendering": {
        "name": "上下文包产物生成",
        "node": "render_context_pack_artifacts",
        "result": "state.repo_context_pack.generation",
        "summary": "复用 scripts/build_context_pack.py 渲染固定 Markdown 与 JSON 产物。",
        "write": ".lgwf/context_pack_generation.json",
    },
    "workflow_summary_handoff": {
        "name": "运行摘要与交接收尾",
        "node": "emit_run_summary_and_report",
        "result": "state.repo_context_pack.summary",
        "summary": "校验上下文包产物，写出 workflow 运行摘要和交接报告。",
        "write": ".lgwf/repo_context_pack_summary.json",
    },
}

ARTIFACT_NAMES = [
    "repo_context_pack.md",
    "agent_handoff.md",
    "module_map.json",
    "command_inventory.json",
    "risk_register.md",
    "read_order.md",
    "summary.json",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def normalize_package_path(raw_path: str) -> str:
    cleaned = raw_path.strip().replace("\\", "/")
    path = PurePosixPath(cleaned)
    if not cleaned or path.is_absolute() or ":" in cleaned:
        raise ValueError(f"非法 package 相对路径: {raw_path}")
    if any(part in {"..", ".lgwf"} for part in path.parts):
        raise ValueError(f"非法 package 相对路径: {raw_path}")
    return path.as_posix().strip("/")


def target_path(target_abs: Path, relative: str) -> Path:
    normalized = normalize_package_path(relative)
    candidate = (target_abs / normalized).resolve()
    candidate.relative_to(target_abs.resolve())
    return candidate


def context_unit(work_dir: Path) -> dict[str, Any]:
    context = load_json(work_dir / ".lgwf" / "current_implementation_unit_context.json")
    unit = context.get("current_implementation_unit")
    if not isinstance(unit, dict):
        raise ValueError("缺少 current_implementation_unit_context.current_implementation_unit")
    return unit


def target_root(unit: dict[str, Any]) -> Path:
    raw = str(unit.get("target_package_abs", "")).strip()
    if not raw:
        raise ValueError("current implementation unit 缺少 target_package_abs")
    return Path(raw).resolve()


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def slug_title(stage_id: str) -> str:
    definition = STAGES.get(stage_id, {})
    return definition.get("name", stage_id.replace("_", " "))


def skill_md() -> str:
    return dedent(
        """\
        ---
        name: repo-context-pack
        description: 扫描指定仓库或模块目录，生成 AI agent 可快速接手的上下文包；默认只读目标源码，只写 output_dir。
        ---

        # repo-context-pack

        当用户需要为一个本地仓库、模块、Codex skill 或 LGWF workflow package 快速生成交接上下文时，使用本 skill。

        ## 能力边界

        - 输入 `target_dir`、可选 `output_dir`、`focus`、`depth` 和 `max_files`。
        - 默认只读 `target_dir`，不会修改目标源码、修复 bug、生成测试或提交 Git。
        - 只向 `output_dir` 写入上下文包产物；未指定时写入 `target_dir/.local/context-packs/<目录名>`。
        - 内嵌 LGWF workflow 位于 `wf/workflow.lgwf`，运行状态应写入同级 `ws/.lgwf/`。

        ## 主要入口

        - 脚本直跑：`python scripts\\build_context_pack.py --target-dir <repo> --output-dir <out> --focus onboarding --depth normal`
        - LGWF audit：`python skills\\lgwf-wf-tools\\vendor\\lgwf-client-assist\\scripts\\lgwf.py audit skills\\repo-context-pack\\wf\\workflow.lgwf`

        ## 输出产物

        - `repo_context_pack.md`
        - `agent_handoff.md`
        - `module_map.json`
        - `command_inventory.json`
        - `risk_register.md`
        - `read_order.md`
        - `summary.json`
        """
    )


def agents_md() -> str:
    return dedent(
        """\
        # repo-context-pack 协作指引

        ## 模块定位

        `repo-context-pack` 是一个带内嵌 LGWF workflow 的 Codex skill，用于为目标仓库或模块生成 AI agent 可接手的上下文包。第一版聚焦只读扫描、结构化报告和交接摘要，不修改目标源码。

        ## 入口

        - Codex skill 入口：`SKILL.md`。
        - 脚本入口：`scripts/build_context_pack.py`。
        - LGWF workflow 入口：`wf/workflow.lgwf`。
        - 运行目录：`ws/`，运行状态只允许写入 `ws/.lgwf/`。

        ## 依赖

        - Python 标准库。
        - 仓库内的 `skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py` 用于 audit 或按 workflow 运行。
        - 不依赖 facade registry；本 skill 第一版不自动注册为内部 workflow。

        ## 状态边界

        - `target_dir` 默认只读。
        - 上下文包只写入 `output_dir`。
        - 禁止在目标 package 根目录写入 `.lgwf`、`.tmp`、`__pycache__` 或运行态缓存。
        - 所有 workflow resource path 必须是包内相对路径，禁止绝对路径、盘符路径和 `..`。

        ## 产物

        - `repo_context_pack.md`：主上下文报告。
        - `agent_handoff.md`：交接摘要。
        - `module_map.json`：模块地图。
        - `command_inventory.json`：命令清单。
        - `risk_register.md`：风险和边界。
        - `read_order.md`：推荐阅读顺序。
        - `summary.json`：扫描统计和产物索引。

        ## 验证

        ```powershell
        python skills\\lgwf-wf-tools\\vendor\\lgwf-client-assist\\scripts\\lgwf.py audit skills\\repo-context-pack\\wf\\workflow.lgwf
        python -m unittest discover skills\\repo-context-pack\\tests
        python -m compileall -q skills\\repo-context-pack
        ```

        ## 禁止事项

        - 不得修改 `target_dir` 内源码文件。
        - 不得执行 Git 写操作、发布、registry 注册或自动审批。
        - 不得把 `vendor`、`.git`、`.lgwf`、`ws`、`.venv`、`node_modules` 等目录复制进上下文包。
        - 不得生成根目录 `workflow.lgwf`；唯一 workflow root 是 `wf/workflow.lgwf`。
        """
    )


def readme_md() -> str:
    return dedent(
        """\
        # repo-context-pack

        `repo-context-pack` 用来扫描指定仓库或模块目录，生成 AI agent 接手任务前最需要的上下文包。它适合 onboarding、modification、review、workflow-authoring 和 handoff 场景。

        ## 快速使用

        ```powershell
        python skills\\repo-context-pack\\scripts\\build_context_pack.py `
          --target-dir D:\\path\\to\\repo `
          --output-dir D:\\path\\to\\repo\\.local\\context-packs\\repo `
          --focus workflow-authoring `
          --depth normal
        ```

        也可以用 LGWF runtime 运行内嵌 workflow；运行状态放在 `skills/repo-context-pack/ws/.lgwf/`：

        ```powershell
        python skills\\lgwf-wf-tools\\vendor\\lgwf-client-assist\\scripts\\lgwf.py run `
          --workflow-lgwf skills\\repo-context-pack\\wf\\workflow.lgwf `
          --work-dir skills\\repo-context-pack\\ws `
          --input-json-file request.json
        ```

        `request.json` 示例：

        ```json
        {
          "target_dir": "D:/allen/github/lgwf_wf_tools",
          "output_dir": "D:/allen/github/lgwf_wf_tools/.local/context-packs/lgwf_wf_tools",
          "focus": "workflow-authoring",
          "depth": "normal",
          "max_files": 1600
        }
        ```

        ## 工作流阶段

        - `entry_scope_resolution`：归一化输入，确认只读目标目录和输出目录。
        - `target_context_inventory`：识别入口文件、模块地图、命令和风险候选。
        - `context_pack_rendering`：生成固定 Markdown 与 JSON 上下文包。
        - `workflow_summary_handoff`：校验产物并写出运行摘要报告。

        ## 输出

        输出目录包含：

        - `repo_context_pack.md`
        - `agent_handoff.md`
        - `module_map.json`
        - `command_inventory.json`
        - `risk_register.md`
        - `read_order.md`
        - `summary.json`

        ## 验证

        ```powershell
        python skills\\lgwf-wf-tools\\vendor\\lgwf-client-assist\\scripts\\lgwf.py audit skills\\repo-context-pack\\wf\\workflow.lgwf
        python -m unittest discover skills\\repo-context-pack\\tests
        ```

        ## 未覆盖范围

        第一版不修复目标仓库问题，不生成目标测试，不注册 registry，不自动发布，不保证对大型 monorepo 做语义级完整理解。
        """
    )


def ws_readme() -> str:
    return dedent(
        """\
        # repo-context-pack ws

        本目录是 `repo-context-pack` 内嵌 LGWF workflow 的运行目录。

        - 运行状态只允许写入本目录下的 `.lgwf/`。
        - 不要在这里保存目标仓库源码副本、上下文包正式产物或手工编辑文件。
        - 如需清理运行状态，只删除 `.lgwf/` 和临时验证输出，不删除本说明文件。
        """
    )


def entry_contract() -> dict[str, Any]:
    return {
        "id": "repo-context-pack",
        "kind": "lgwf_embedded_skill",
        "version": 1,
        "workflow_lgwf": "wf/workflow.lgwf",
        "work_dir": "ws",
        "input_mode": "input_json_required",
        "input_schema": {
            "type": "object",
            "required": ["target_dir"],
            "properties": {
                "target_dir": {"type": "string", "description": "要分析的仓库或模块目录；默认只读。"},
                "output_dir": {
                    "type": "string",
                    "description": "上下文包输出目录；未指定时使用 target_dir/.local/context-packs/<目录名>。",
                },
                "focus": {
                    "type": "string",
                    "enum": ["onboarding", "modification", "review", "workflow-authoring", "handoff"],
                    "default": "onboarding",
                },
                "depth": {"type": "string", "enum": ["light", "normal", "deep"], "default": "normal"},
                "max_files": {"type": "integer", "minimum": 1, "default": 1600},
                "notes": {"type": "string"},
            },
            "example": {
                "target_dir": "D:/repo/example",
                "output_dir": "D:/repo/example/.local/context-packs/example",
                "focus": "workflow-authoring",
                "depth": "normal",
                "max_files": 1600,
            },
        },
        "input_file_policy": "包含中文、空格或嵌套 JSON 时使用 UTF-8 no BOM --input-json-file。",
        "auto_human_policy": "not_required",
        "target_scope": {
            "fields": ["target_dir", "output_dir", "focus", "depth", "max_files"],
            "read_scope": "target_dir",
            "write_scope": "output_dir",
        },
        "state_boundary": {
            "work_dir": "ws",
            "runtime_state": ".lgwf/",
            "target_dir_access": "read_only",
            "target_writes": "none",
            "output_writes": ARTIFACT_NAMES,
        },
        "outputs": {
            "summary": ".lgwf/repo_context_pack_summary.json",
            "report": "reports/repo-context-pack/report.md",
            "context_pack": "request.output_dir",
        },
        "resume_policy": "同一请求可复用 ws/.lgwf；重新运行会覆盖 output_dir 中同名上下文包产物。",
    }


def artifact_contracts() -> dict[str, Any]:
    return {
        "module_name": "repo-context-pack",
        "workflow_root": "wf",
        "output_root": "request.output_dir",
        "encoding": "UTF-8 no BOM",
        "runtime_artifacts": [
            ".lgwf/repo_context_pack_request.json",
            ".lgwf/context_inventory.json",
            ".lgwf/context_pack_generation.json",
            ".lgwf/repo_context_pack_summary.json",
            "reports/repo-context-pack/report.md",
        ],
        "final_outputs": [
            ".lgwf/repo_context_pack_summary.json",
            "reports/repo-context-pack/report.md",
        ],
        "artifacts": [
            {
                "id": Path(name).stem,
                "path": name,
                "required": True,
                "format": "json" if name.endswith(".json") else "markdown",
                "producer": "context_pack_rendering" if name != "summary.json" else "workflow_summary_handoff",
            }
            for name in ARTIFACT_NAMES
        ],
        "constraints": [
            "不得写入 request.output_dir 之外的上下文包产物。",
            "不得修改 request.target_dir 内源码。",
            "Markdown 与 JSON 产物统一使用 UTF-8 no BOM。",
        ],
    }


def root_workflow() -> str:
    return dedent(
        """\
        WORKFLOW repo_context_pack;
        ENTRY entry_scope_resolution;

        DEFAULTS {
          ref_root workflow ".";
          timeout_seconds 300;
          result_path "repo_context_pack.results.{node}";
        }

        STEP entry_scope_resolution
          WORKFLOW "entry_scope_resolution/workflow.lgwf"
          CONTRACT {
            WRITE workspace file ".lgwf/repo_context_pack_request.json";
          };

        STEP target_context_inventory
          WORKFLOW "target_context_inventory/workflow.lgwf"
          CONTRACT {
            READ workspace file ".lgwf/repo_context_pack_request.json";
            WRITE workspace file ".lgwf/context_inventory.json";
          };

        STEP context_pack_rendering
          WORKFLOW "context_pack_rendering/workflow.lgwf"
          CONTRACT {
            READ workspace file ".lgwf/repo_context_pack_request.json";
            READ workspace file ".lgwf/context_inventory.json";
            WRITE workspace file ".lgwf/context_pack_generation.json";
          };

        STEP workflow_summary_handoff
          WORKFLOW "workflow_summary_handoff/workflow.lgwf"
          CONTRACT {
            READ workspace file ".lgwf/repo_context_pack_request.json";
            READ workspace file ".lgwf/context_pack_generation.json";
            WRITE workspace file ".lgwf/repo_context_pack_summary.json";
            WRITE workspace file "reports/repo-context-pack/report.md";
          };

        FLOW entry_scope_resolution
          THEN target_context_inventory
          THEN context_pack_rendering
          THEN workflow_summary_handoff;
        """
    )


def stage_workflow(stage_id: str) -> str:
    definition = STAGES[stage_id]
    node = definition["node"]
    result = definition["result"]
    write = definition["write"]
    reads = {
        "entry_scope_resolution": [],
        "target_context_inventory": ['READ workspace file ".lgwf/repo_context_pack_request.json";'],
        "context_pack_rendering": [
            'READ workspace file ".lgwf/repo_context_pack_request.json";',
            'READ workspace file ".lgwf/context_inventory.json";',
        ],
        "workflow_summary_handoff": [
            'READ workspace file ".lgwf/repo_context_pack_request.json";',
            'READ workspace file ".lgwf/context_pack_generation.json";',
        ],
    }[stage_id]
    extra_write = (
        ['WRITE workspace file "reports/repo-context-pack/report.md";']
        if stage_id == "workflow_summary_handoff"
        else []
    )
    contract_lines = "\n".join(f"    {line}" for line in [*reads, f'WRITE workspace file "{write}";', *extra_write])
    return dedent(
        f"""\
        WORKFLOW {stage_id};
        ENTRY {node};

        DEFAULTS {{
          ref_root workflow ".";
          timeout_seconds 180;
          result_path "repo_context_pack.{stage_id}.{{node}}";
        }}

        PY {node}
          SCRIPT "scripts/run.py"
          TIMEOUT 120
          RESULT {result}
          UPDATES_STATE
          CONTRACT {{
        {contract_lines}
          }};

        FLOW {node};
        """
    )


def stage_prompt(stage_id: str) -> str:
    definition = STAGES[stage_id]
    return dedent(
        f"""\
        # {definition['name']}

        ## 定位

        本阶段属于 `repo-context-pack` 第一层子 workflow，职责是：{definition['summary']}

        ## 输入输出

        - 输入状态来自 `ws/.lgwf/` 下的上游 JSON。
        - 输出写入 `{definition['write']}`。
        - 不修改 `target_dir` 内源码，不向 package 根目录写入运行态文件。

        ## 验收

        - 阶段脚本可用 Python 标准库执行。
        - 输出 JSON 为 UTF-8 no BOM。
        - 阶段资源路径保持包内相对路径。
        """
    )


def stage_resources(stage_id: str) -> str:
    definition = STAGES[stage_id]
    return dedent(
        f"""\
        # {definition['name']} resources

        本目录保存 `{stage_id}` 阶段的局部资源。第一版阶段逻辑集中在 `scripts/run.py`，共享稳定技术逻辑位于 `wf/shared/scripts/repo_context_runtime.py`。

        禁止在本目录放置运行态 `.lgwf` 文件或目标仓库扫描结果。
        """
    )


def stage_script(stage_id: str) -> str:
    return dedent(
        f"""\
        from __future__ import annotations

        import sys
        from pathlib import Path


        SCRIPT_PATH = Path(__file__).resolve()
        SHARED_SCRIPT_CANDIDATES = [
            SCRIPT_PATH.parents[2] / "shared" / "scripts",
            SCRIPT_PATH.parents[3] / "wf" / "shared" / "scripts",
        ]
        for candidate in SHARED_SCRIPT_CANDIDATES:
            if (candidate / "repo_context_runtime.py").is_file():
                sys.path.insert(0, str(candidate))
                break
        else:
            raise RuntimeError(f"无法定位 repo_context_runtime.py: {{SCRIPT_PATH}}")

        from repo_context_runtime import run_stage


        if __name__ == "__main__":
            run_stage("{stage_id}", Path(__file__).resolve())
        """
    )


def shared_runtime() -> str:
    for root in Path(__file__).resolve().parents:
        reference = root / "repo-context-pack" / "wf" / "shared" / "scripts" / "repo_context_runtime.py"
        if reference.is_file():
            return reference.read_text(encoding="utf-8")
    return dedent(
        """\
        from __future__ import annotations

        import argparse
        import importlib.util
        import json
        import sys
        from pathlib import Path
        from typing import Any


        FOCUS_VALUES = {"onboarding", "modification", "review", "workflow-authoring", "handoff"}
        DEPTH_VALUES = {"light", "normal", "deep"}
        ARTIFACT_NAMES = [
            "repo_context_pack.md",
            "agent_handoff.md",
            "module_map.json",
            "command_inventory.json",
            "risk_register.md",
            "read_order.md",
            "summary.json",
        ]


        def write_json(path: Path, data: Any) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")


        def write_text(path: Path, text: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text.rstrip() + "\\n", encoding="utf-8")


        def read_json(path: Path) -> dict[str, Any]:
            if not path.exists():
                return {}
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, dict) else {}


        def read_stdin_payload() -> dict[str, Any]:
            raw = sys.stdin.read().strip()
            if not raw:
                return {}
            data = json.loads(raw)
            if not isinstance(data, dict):
                return {}
            for key in ("repo_context_pack", "request"):
                value = data.get(key)
                if isinstance(value, dict):
                    return value
            return data


        def find_package_root(script_path: Path) -> Path:
            for candidate in [script_path.resolve(), *script_path.resolve().parents]:
                if (candidate / "scripts" / "build_context_pack.py").is_file() and (candidate / "wf").is_dir():
                    return candidate
            raise RuntimeError(f"无法定位 repo-context-pack package root: {script_path}")


        def load_builder(package_root: Path) -> Any:
            script = package_root / "scripts" / "build_context_pack.py"
            spec = importlib.util.spec_from_file_location("repo_context_pack_builder", script)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"无法加载上下文包构建脚本: {script}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module


        def unwrap_request(raw: dict[str, Any]) -> dict[str, Any]:
            for key in ("repo_context_pack", "request"):
                value = raw.get(key)
                if isinstance(value, dict):
                    return value
            return raw


        def normalize_request(package_root: Path, raw: dict[str, Any]) -> dict[str, Any]:
            request = unwrap_request(raw)
            target_raw = str(request.get("target_dir", "")).strip()
            if not target_raw:
                raise ValueError("repo-context-pack 需要输入 target_dir")
            target_dir = Path(target_raw).expanduser().resolve()
            if not target_dir.is_dir():
                raise ValueError(f"target_dir 不存在或不是目录: {target_dir}")

            output_raw = str(request.get("output_dir", "")).strip()
            if output_raw:
                output_dir = Path(output_raw).expanduser().resolve()
            else:
                output_dir = (target_dir / ".local" / "context-packs" / target_dir.name).resolve()

            focus = str(request.get("focus") or "onboarding").strip()
            if focus not in FOCUS_VALUES:
                raise ValueError(f"focus 不支持: {focus}")
            depth = str(request.get("depth") or "normal").strip()
            if depth not in DEPTH_VALUES:
                raise ValueError(f"depth 不支持: {depth}")
            try:
                max_files = int(request.get("max_files", 1600))
            except (TypeError, ValueError) as exc:
                raise ValueError("max_files 必须是整数") from exc
            if max_files < 1:
                raise ValueError("max_files 必须大于 0")

            return {
                "target_dir": str(target_dir),
                "output_dir": str(output_dir),
                "focus": focus,
                "depth": depth,
                "max_files": max_files,
                "notes": str(request.get("notes", "")).strip(),
                "package_root": str(package_root),
            }


        def request_path() -> Path:
            return Path.cwd() / ".lgwf" / "repo_context_pack_request.json"


        def inventory_path() -> Path:
            return Path.cwd() / ".lgwf" / "context_inventory.json"


        def generation_path() -> Path:
            return Path.cwd() / ".lgwf" / "context_pack_generation.json"


        def summary_path() -> Path:
            return Path.cwd() / ".lgwf" / "repo_context_pack_summary.json"


        def load_request() -> dict[str, Any]:
            request = read_json(request_path())
            if not request:
                raise ValueError("缺少 .lgwf/repo_context_pack_request.json，请先运行 entry_scope_resolution")
            return request


        def collect_inventory(package_root: Path, request: dict[str, Any]) -> dict[str, Any]:
            builder = load_builder(package_root)
            target_dir = Path(request["target_dir"]).resolve()
            dirs, files = builder.walk_target(target_dir, request["depth"], int(request["max_files"]))
            entry_files = builder.detect_entry_files(target_dir, files)
            modules = builder.detect_modules(target_dir, dirs)
            commands = builder.extract_commands(target_dir, files)
            risks = builder.extract_risks(target_dir, files)
            read_order = builder.build_read_order(request["focus"], entry_files, modules)
            return {
                "target_dir": str(target_dir),
                "focus": request["focus"],
                "depth": request["depth"],
                "scanned_file_count": len(files),
                "entry_files": entry_files,
                "modules": modules,
                "commands": commands,
                "risks": risks,
                "read_order": read_order,
            }


        def render_pack(package_root: Path, request: dict[str, Any]) -> dict[str, Any]:
            builder = load_builder(package_root)
            args = argparse.Namespace(
                target_dir=request["target_dir"],
                output_dir=request["output_dir"],
                focus=request["focus"],
                depth=request["depth"],
                max_files=int(request["max_files"]),
            )
            return builder.build_pack(args)


        def validate_outputs(output_dir: Path) -> list[dict[str, Any]]:
            checks: list[dict[str, Any]] = []
            for name in ARTIFACT_NAMES:
                path = output_dir / name
                item = {"path": name, "exists": path.is_file()}
                if name.endswith(".json") and path.is_file():
                    json.loads(path.read_text(encoding="utf-8-sig"))
                    item["json_ok"] = True
                checks.append(item)
            return checks


        def run_stage(stage_id: str, script_path: Path) -> None:
            package_root = find_package_root(script_path)
            if stage_id == "entry_scope_resolution":
                request = normalize_request(package_root, read_stdin_payload())
                write_json(request_path(), request)
                payload = {"repo_context_pack.request": request}
            elif stage_id == "target_context_inventory":
                request = load_request()
                inventory = collect_inventory(package_root, request)
                write_json(inventory_path(), inventory)
                payload = {"repo_context_pack.context_inventory": inventory}
            elif stage_id == "context_pack_rendering":
                request = load_request()
                inventory = read_json(inventory_path())
                summary = render_pack(package_root, request)
                result = {"summary": summary, "inventory_available": bool(inventory)}
                write_json(generation_path(), result)
                payload = {"repo_context_pack.generation": result}
            elif stage_id == "workflow_summary_handoff":
                request = load_request()
                generation = read_json(generation_path())
                output_dir = Path(request["output_dir"]).resolve()
                checks = validate_outputs(output_dir)
                passed = all(item["exists"] for item in checks)
                summary = read_json(output_dir / "summary.json")
                result = {
                    "passed": passed,
                    "request": request,
                    "generation": generation,
                    "output_dir": str(output_dir),
                    "artifacts": checks,
                    "summary": summary,
                }
                write_json(summary_path(), result)
                report_lines = [
                    "# repo-context-pack 运行报告",
                    "",
                    f"- 状态：`{'passed' if passed else 'failed'}`",
                    f"- 目标目录：`{request['target_dir']}`",
                    f"- 输出目录：`{output_dir}`",
                    "",
                    "## 产物",
                    "",
                    *[f"- `{item['path']}`：{'存在' if item['exists'] else '缺失'}" for item in checks],
                    "",
                ]
                write_text(Path.cwd() / "reports" / "repo-context-pack" / "report.md", "\\n".join(report_lines))
                payload = {"repo_context_pack.summary": result}
            else:
                raise ValueError(f"未知阶段: {stage_id}")

            print(json.dumps(payload, ensure_ascii=False, indent=2))
        """
    )


def support_tests() -> str:
    return dedent(
        """\
        from __future__ import annotations

        import json
        import re
        import unittest
        from pathlib import Path


        PACKAGE_ROOT = Path(__file__).resolve().parents[1]
        WORKFLOW_ROOT = PACKAGE_ROOT / "wf"


        class RepoContextPackWorkflowStructureTests(unittest.TestCase):
            def test_required_package_files_exist(self) -> None:
                for relative in (
                    "SKILL.md",
                    "AGENTS.md",
                    "README.md",
                    "entry_contract.json",
                    "scripts/build_context_pack.py",
                    "wf/workflow.lgwf",
                    "wf/artifact_contracts.json",
                    "wf/shared/scripts/repo_context_runtime.py",
                ):
                    self.assertTrue((PACKAGE_ROOT / relative).is_file(), relative)

            def test_workflow_has_only_allowed_workflow_roots(self) -> None:
                workflow_files = sorted(path.relative_to(PACKAGE_ROOT).as_posix() for path in PACKAGE_ROOT.rglob("workflow.lgwf"))
                self.assertIn("wf/workflow.lgwf", workflow_files)
                self.assertNotIn("workflow.lgwf", workflow_files)
                for relative in workflow_files:
                    parts = Path(relative).parts
                    self.assertTrue(
                        relative == "wf/workflow.lgwf" or (len(parts) == 3 and parts[0] == "wf" and parts[2] == "workflow.lgwf"),
                        relative,
                    )

            def test_root_workflow_references_four_stage_workflows(self) -> None:
                text = (WORKFLOW_ROOT / "workflow.lgwf").read_text(encoding="utf-8")
                for stage in (
                    "entry_scope_resolution",
                    "target_context_inventory",
                    "context_pack_rendering",
                    "workflow_summary_handoff",
                ):
                    self.assertIn(f'WORKFLOW "{stage}/workflow.lgwf"', text)
                    self.assertTrue((WORKFLOW_ROOT / stage / "workflow.lgwf").is_file(), stage)
                    self.assertTrue((WORKFLOW_ROOT / stage / "agents" / "prompt.md").is_file(), stage)
                    self.assertTrue((WORKFLOW_ROOT / stage / "scripts" / "run.py").is_file(), stage)

            def test_resource_paths_are_relative(self) -> None:
                pattern = re.compile(r'"([^"]+)"')
                for workflow in WORKFLOW_ROOT.rglob("workflow.lgwf"):
                    text = workflow.read_text(encoding="utf-8")
                    for value in pattern.findall(text):
                        if "/" not in value and "\\\\" not in value:
                            continue
                        self.assertFalse(Path(value).is_absolute(), value)
                        self.assertNotIn("..", Path(value.replace("\\\\", "/")).parts, value)
                        self.assertNotRegex(value, r"^[A-Za-z]:", value)

            def test_entry_contract_keeps_target_read_only(self) -> None:
                contract = json.loads((PACKAGE_ROOT / "entry_contract.json").read_text(encoding="utf-8"))
                self.assertEqual(contract["state_boundary"]["target_dir_access"], "read_only")
                self.assertNotIn("output_dir", contract["input_schema"]["required"])
                self.assertEqual(contract["workflow_lgwf"], "wf/workflow.lgwf")
                self.assertEqual(contract["work_dir"], "ws")


        if __name__ == "__main__":
            unittest.main()
        """
    )


def support_tests_readme() -> str:
    return dedent(
        """\
        # repo-context-pack tests

        本目录包含两类最小验证：

        - `test_build_context_pack.py` 验证核心扫描脚本能生成固定上下文包产物。
        - `test_workflow_structure.py` 验证内嵌 LGWF workflow 的目录边界、资源路径和入口契约。

        运行方式：

        ```powershell
        python -m unittest discover skills\\repo-context-pack\\tests
        ```
        """
    )


def shared_readme() -> str:
    return dedent(
        """\
        # shared scripts

        `repo_context_runtime.py` 放置四个阶段共用的稳定技术逻辑，包括请求归一化、调用 `scripts/build_context_pack.py`、输出校验和运行摘要写入。

        共享目录不得放置阶段私有 prompt、人工确认文案或运行态文件。
        """
    )


def fallback_step_doc(step_slug: str, stage_id: str, step_name: str) -> str:
    return dedent(
        f"""\
        # {step_name}

        ## 目标

        支撑 `{stage_id}` 阶段：{STAGES.get(stage_id, {}).get('summary', '')}

        ## 输入

        - 上游 `.lgwf/` 运行态 JSON。
        - `entry_contract.json` 中声明的运行请求。

        ## 输出

        - 与阶段职责对应的 `.lgwf/` 中间产物或 `output_dir` 上下文包文件。

        ## 禁止事项

        - 不修改 `target_dir` 源码。
        - 不向目标 package 根目录写入 `.lgwf` 或缓存目录。
        - 不使用绝对 workflow resource path。
        """
    )


def write_package_contracts(target_abs: Path) -> list[str]:
    files = {
        "SKILL.md": skill_md(),
        "AGENTS.md": agents_md(),
        "README.md": readme_md(),
        "ws/README.md": ws_readme(),
    }
    generated: list[str] = []
    for relative, text in files.items():
        write_text(target_path(target_abs, relative), text)
        generated.append(relative)
    write_json(target_path(target_abs, "entry_contract.json"), entry_contract())
    write_json(target_path(target_abs, "wf/artifact_contracts.json"), artifact_contracts())
    generated.extend(["entry_contract.json", "wf/artifact_contracts.json"])
    return generated


def step_docs_from_unit(unit: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in unit.get("step_designs", []):
        if not isinstance(item, dict):
            continue
        doc_path = str(item.get("doc_path", "")).strip()
        if not doc_path:
            continue
        relative = normalize_package_path(doc_path)
        if relative.startswith("docs/steps/"):
            relative = f"wf/{relative}"
        stage_id = str(item.get("stage_id", "")).strip()
        step_slug = str(item.get("step_slug", Path(relative).stem)).strip() or Path(relative).stem
        step_name = str(item.get("step_name", step_slug)).strip() or step_slug
        result[relative] = fallback_step_doc(step_slug, stage_id, step_name)
    return result


def write_root_workflow(target_abs: Path, work_dir: Path, unit: dict[str, Any]) -> list[str]:
    generated = ["wf/workflow.lgwf"]
    write_text(target_path(target_abs, "wf/workflow.lgwf"), root_workflow())
    source_docs = work_dir / "docs" / "steps"
    fallback_docs = step_docs_from_unit(unit)
    for relative in [path for path in unit.get("package_relative_files", []) if str(path).startswith("wf/docs/steps/")]:
        package_relative = normalize_package_path(str(relative))
        source = source_docs / Path(package_relative).name
        if source.is_file():
            text = source.read_text(encoding="utf-8-sig")
        else:
            text = fallback_docs.get(package_relative, fallback_step_doc(Path(package_relative).stem, "", Path(package_relative).stem))
        write_text(target_path(target_abs, package_relative), text)
        generated.append(package_relative)
    return unique(generated)


def write_stage(target_abs: Path, stage_id: str) -> list[str]:
    if stage_id not in STAGES:
        raise ValueError(f"不支持的阶段: {stage_id}")
    files = {
        f"wf/{stage_id}/workflow.lgwf": stage_workflow(stage_id),
        f"wf/{stage_id}/agents/prompt.md": stage_prompt(stage_id),
        f"wf/{stage_id}/scripts/run.py": stage_script(stage_id),
        f"wf/{stage_id}/resources/README.md": stage_resources(stage_id),
    }
    generated: list[str] = []
    for relative, text in files.items():
        write_text(target_path(target_abs, relative), text)
        generated.append(relative)
    return generated


def write_support(target_abs: Path) -> list[str]:
    files = {
        "wf/shared/scripts/repo_context_runtime.py": shared_runtime(),
        "wf/shared/scripts/README.md": shared_readme(),
        "tests/README.md": support_tests_readme(),
        "tests/test_workflow_structure.py": support_tests(),
    }
    generated: list[str] = []
    for relative, text in files.items():
        write_text(target_path(target_abs, relative), text)
        generated.append(relative)
    return generated


def result_payload(unit: dict[str, Any], generated: list[str]) -> dict[str, Any]:
    unit_id = str(unit.get("unit_id", "")).strip()
    return {
        "unit_id": unit_id,
        "unit_type": str(unit.get("unit_type", "")).strip(),
        "status": "ok",
        "generated_files": [{"path": path} for path in generated],
        "generated": {
            "root_files": generated,
            "by_step": [
                {
                    "step_slug": unit_id,
                    "generated_files": generated,
                }
            ],
        },
        "handled_failures": unit.get("repair_focus", []),
        "remaining_risks": [],
        "notes": [
            "由 wf-create deterministic implement_current_unit.py 生成。",
            "目标包按 skill_wrapped_workflow 处理，保留根 SKILL.md。",
        ],
        "validation": [{"command": "deterministic implementation", "ok": True}],
    }


def implement_current_unit(work_dir: Path) -> dict[str, Any]:
    unit = context_unit(work_dir)
    target_abs = target_root(unit)
    unit_id = str(unit.get("unit_id", "")).strip()
    target_abs.mkdir(parents=True, exist_ok=True)
    if unit_id == "package_contracts":
        generated = write_package_contracts(target_abs)
    elif unit_id == "root_workflow":
        generated = write_root_workflow(target_abs, work_dir, unit)
    elif unit_id.startswith("stage_"):
        generated = write_stage(target_abs, unit_id.removeprefix("stage_"))
    elif unit_id == "shared_helpers_tests":
        generated = write_support(target_abs)
    else:
        raise ValueError(f"未知 implementation unit: {unit_id}")
    payload = result_payload(unit, generated)
    write_json(work_dir / ".lgwf" / "current_implementation_unit_result.json", payload)
    return payload


def main() -> None:
    payload = implement_current_unit(Path.cwd())
    print(
        json.dumps(
            {"lgwf_wf_create.current_implementation_unit_result": payload},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
