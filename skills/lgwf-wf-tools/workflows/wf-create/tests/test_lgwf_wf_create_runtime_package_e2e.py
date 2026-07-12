from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = PACKAGE_ROOT.parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[5]
WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"
LGWF = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
VENDOR_ROOT = FACADE_ROOT / "vendor" / "lgwf-client-assist"


WORKFLOW_NAME = "runtime_e2e_created"
TARGET_PACKAGE_ROOT = "skills/runtime-e2e-created"
STAGES = ["01_collect_context", "02_run_checks"]


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_lgwf(args: list[str], *, env: dict[str, str], timeout: int = 240) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LGWF), *args],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def runtime_temp_dir(stack: ExitStack) -> str:
    if os.environ.get("LGWF_WF_CREATE_RUNTIME_E2E_KEEP_WORKDIR") == "1":
        return tempfile.mkdtemp(prefix="lgwf-wf-create-runtime-e2e-")
    return stack.enter_context(
        tempfile.TemporaryDirectory(prefix="lgwf-wf-create-runtime-e2e-", ignore_cleanup_errors=True)
    )


def write_prompt_file_mode_patch(patch_dir: Path) -> None:
    patch_dir.mkdir(parents=True, exist_ok=True)
    (patch_dir / "sitecustomize.py").write_text(
        r'''
from __future__ import annotations

import json
import os
import pathlib
import uuid


if os.environ.get("LGWF_FAKE_CODEX_PROMPT_FILE_MODE") == "1":
    import lgwf_client.process_execution as process_execution

    _original_resolve = process_execution.CommandResolver.resolve

    def _extract_main_prompt_path(prompt: str) -> str:
        lines = prompt.splitlines()
        for index, line in enumerate(lines[:-1]):
            if line.strip() == "Main prompt file:":
                return lines[index + 1].strip().replace("\\", "/")
        return ""

    def _resolve_with_prompt_file(self, command):
        if (
            isinstance(command, list)
            and len(command) >= 2
            and str(command[0]).lower() == "codex"
            and isinstance(command[-1], str)
            and command[-1].startswith("# LGWF Codex Handoff")
        ):
            work_dir = pathlib.Path(os.environ.get("LGWF_FAKE_CODEX_ROOT_WORK_DIR") or pathlib.Path.cwd())
            prompt_root = work_dir / ".lgwf" / "fake_codex_prompts" / uuid.uuid4().hex
            prompt_root.mkdir(parents=True, exist_ok=True)
            prompt_path = prompt_root / "handoff_prompt.txt"
            prompt_path.write_text(command[-1], encoding="utf-8")
            (prompt_root / "metadata.json").write_text(
                json.dumps({"main_prompt_path": _extract_main_prompt_path(command[-1])}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            command = [*command[:-1], "--prompt-file", str(prompt_path)]
        return _original_resolve(self, command)

    process_execution.CommandResolver.resolve = _resolve_with_prompt_file
'''.lstrip(),
        encoding="utf-8",
    )


def write_fake_codex(fake_root: Path) -> None:
    fake_root.mkdir(parents=True, exist_ok=True)
    fake_script = fake_root / "fake_codex.py"
    fake_script.write_text(
        r'''
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Any


WORKFLOW_NAME = "runtime_e2e_created"
TARGET_PACKAGE_ROOT = "skills/runtime-e2e-created"
STAGES = ["01_collect_context", "02_run_checks"]


def write_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_handoff_prompt(argv: list[str]) -> str:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("--prompt-file")
    known, unknown = parser.parse_known_args(argv[1:])
    if known.prompt_file:
        return pathlib.Path(known.prompt_file).read_text(encoding="utf-8")
    for item in unknown:
        if item.startswith("--prompt-file="):
            return pathlib.Path(item.split("=", 1)[1]).read_text(encoding="utf-8")
        if item.startswith("# LGWF Codex Handoff"):
            return item
        candidate = pathlib.Path(item)
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8")
            if "# LGWF Codex Handoff" in text:
                return text
    stdin_text = sys.stdin.read()
    if "# LGWF Codex Handoff" in stdin_text:
        return stdin_text
    return ""


def extract_main_prompt_path(prompt: str) -> str:
    lines = prompt.splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.strip() == "Main prompt file:":
            return lines[index + 1].strip().replace("\\", "/")
    return ""


def prompt_key(prompt: str) -> str:
    normalized = extract_main_prompt_path(prompt)
    snapshot_marker = "/.lgwf/workflow/"
    if snapshot_marker in normalized:
        return "wf/" + normalized.split(snapshot_marker, 1)[1]
    marker = "/wf/"
    if marker in normalized:
        return "wf/" + normalized.split(marker, 1)[1]
    if normalized.startswith("wf/"):
        return normalized
    return normalized


def extract_output_path(prompt: str) -> pathlib.Path | None:
    matches = re.findall(r"Output path:\s*(.+)", prompt)
    if not matches:
        return None
    raw = matches[-1].strip().strip("`")
    return pathlib.Path(raw)


def root_work_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("LGWF_FAKE_CODEX_ROOT_WORK_DIR") or pathlib.Path.cwd())


def current_work_dir() -> pathlib.Path:
    return pathlib.Path.cwd()


def log_call(key: str, output_path: pathlib.Path | None) -> None:
    log = pathlib.Path(os.environ.get("LGWF_FAKE_CODEX_CALL_LOG", str(root_work_dir() / ".lgwf" / "fake_codex_calls.jsonl")))
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"prompt_key": key, "cwd": str(pathlib.Path.cwd()), "output_path": str(output_path or "")}, ensure_ascii=False) + "\n")


def requirements_payload() -> dict[str, Any]:
    return {
        "workflow_name": WORKFLOW_NAME,
        "target_package_root": TARGET_PACKAGE_ROOT,
        "package_profile": "internal_workflow_package",
        "requirements": [
            {
                "id": "r1",
                "description": "创建一个包含两个阶段的内部 LGWF workflow package。",
            }
        ],
        "non_goals": ["不注册 facade registry", "不调用外部服务"],
    }


def business_flow_payload() -> dict[str, Any]:
    return {
        "workflow_name": WORKFLOW_NAME,
        "target_package_root": TARGET_PACKAGE_ROOT,
        "package_profile": "internal_workflow_package",
        "stages": [
            {"stage_id": "01_collect_context", "summary": "收集输入上下文", "human_approval": False},
            {"stage_id": "02_run_checks", "summary": "执行确定性检查", "human_approval": False},
        ],
    }


def step_designs_payload() -> dict[str, Any]:
    return {
        "workflow_name": WORKFLOW_NAME,
        "target_package_root": TARGET_PACKAGE_ROOT,
        "source_business_flow_stages": [
            {"stage_id": "01_collect_context", "summary": "收集输入上下文"},
            {"stage_id": "02_run_checks", "summary": "执行确定性检查"},
        ],
        "step_designs": [
            {
                "stage_id": "01_collect_context",
                "step_slug": "collect_context",
                "doc_path": "docs/steps/collect-context.md",
                "goal": "读取输入并输出上下文摘要。",
            },
            {
                "stage_id": "02_run_checks",
                "step_slug": "run_checks",
                "doc_path": "docs/steps/run-checks.md",
                "goal": "执行确定性检查并输出结果。",
            },
        ],
    }


def package_doc(title: str) -> str:
    return f"""# {title}

## 模块定位

`runtime_e2e_created` 是 wf-create runtime E2E 生成的临时 LGWF workflow package，用于验证创建链路能产出可 audit 的目标包。

## 入口

- workflow root：`wf/workflow.lgwf`
- work dir：`ws/`
- 启动命令：`python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit wf/workflow.lgwf`

## 依赖

- 依赖 `lgwf-client-assist` 执行 authoring audit。
- 不依赖外部网络服务。

## 状态边界

- 运行状态只写入 `ws/.lgwf/`。
- 源码、测试和文档留在 package 目录内。

## 产物

- `wf/workflow.lgwf`
- `wf/01_collect_context/workflow.lgwf`
- `wf/02_run_checks/workflow.lgwf`
- `tests/test_workflow_structure.py`

## 验证

```powershell
python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit wf/workflow.lgwf
python -m unittest discover tests
```

## 禁止事项

- 不得把本临时 package 注册为独立 Codex skill。
- 不得把 `.lgwf` 写入 package 根目录。
- 不得使用绝对 resource path 或 `..`。
"""


def entry_contract() -> dict[str, Any]:
    return {
        "id": WORKFLOW_NAME,
        "kind": "lgwf",
        "version": 1,
        "workflow_lgwf": "wf/workflow.lgwf",
        "work_dir": "ws",
        "input_mode": "input_json_optional",
        "state_boundary": {"work_dir": "ws", "runtime_state": ".lgwf/"},
        "outputs": {"summary": ".lgwf/runtime_e2e_summary.json"},
        "resume_policy": "Use lgwf.py resume with the same work dir.",
    }


def artifact_contracts() -> dict[str, Any]:
    return {
        "artifacts": [
            {"path": ".lgwf/runtime_e2e_summary.json", "kind": "runtime_summary", "producer": "02_run_checks"}
        ]
    }


def root_workflow() -> str:
    return """WORKFLOW runtime_e2e_created;
ENTRY collect_context;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 120;
}

STEP collect_context
  WORKFLOW "01_collect_context/workflow.lgwf"
  CONTRACT {
  };

STEP run_checks
  WORKFLOW "02_run_checks/workflow.lgwf"
  CONTRACT {
  };

FLOW collect_context
  THEN run_checks;
"""


def stage_workflow(stage_id: str) -> str:
    state_name = stage_id.replace("-", "_")
    workflow_name = f"stage_{state_name}"
    return f"""WORKFLOW {workflow_name};
ENTRY run;

DEFAULTS {{
  ref_root workflow ".";
  timeout_seconds 120;
}}

PY run
  SCRIPT "scripts/run.py"
  TIMEOUT 30
  RESULT state.runtime_e2e.{workflow_name}
  UPDATES_STATE
  CONTRACT {{
  }};

FLOW run;
"""


def stage_script(stage_id: str) -> str:
    return f"""from __future__ import annotations

import json


def main() -> None:
    print(json.dumps({{"runtime_e2e.{stage_id}": {{"status": "ok"}}}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
"""


def test_file() -> str:
    return """from __future__ import annotations

import unittest
from pathlib import Path


class RuntimeE2EGeneratedWorkflowStructureTest(unittest.TestCase):
    def test_workflow_files_exist(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "wf" / "workflow.lgwf").is_file())
        self.assertTrue((root / "wf" / "01_collect_context" / "workflow.lgwf").is_file())
        self.assertTrue((root / "wf" / "02_run_checks" / "workflow.lgwf").is_file())


if __name__ == "__main__":
    unittest.main()
"""


def write_package_contracts(target: pathlib.Path) -> list[str]:
    write_text(target / "AGENTS.md", package_doc("runtime_e2e_created agent 指引"))
    write_text(target / "README.md", package_doc("runtime_e2e_created"))
    write_json(target / "entry_contract.json", entry_contract())
    write_json(target / "wf" / "artifact_contracts.json", artifact_contracts())
    return ["AGENTS.md", "README.md", "entry_contract.json", "wf/artifact_contracts.json"]


def write_root_workflow(target: pathlib.Path) -> list[str]:
    write_text(target / "wf" / "workflow.lgwf", root_workflow())
    write_text(target / "wf" / "docs" / "steps" / "collect-context.md", "# collect-context\n\n目标：收集输入上下文。\n")
    write_text(target / "wf" / "docs" / "steps" / "run-checks.md", "# run-checks\n\n目标：执行确定性检查。\n")
    return ["wf/workflow.lgwf", "wf/docs/steps/collect-context.md", "wf/docs/steps/run-checks.md"]


def write_stage(target: pathlib.Path, stage_id: str) -> list[str]:
    stage_root = target / "wf" / stage_id
    write_text(stage_root / "workflow.lgwf", stage_workflow(stage_id))
    write_text(stage_root / "agents" / "prompt.md", f"# {stage_id}\n\n本阶段由确定性脚本执行。\n")
    write_text(stage_root / "scripts" / "run.py", stage_script(stage_id))
    write_text(stage_root / "resources" / "README.md", f"# {stage_id} resources\n")
    return [
        f"wf/{stage_id}/workflow.lgwf",
        f"wf/{stage_id}/agents/prompt.md",
        f"wf/{stage_id}/scripts/run.py",
        f"wf/{stage_id}/resources/README.md",
    ]


def write_support(target: pathlib.Path) -> list[str]:
    write_text(target / "tests" / "README.md", "# tests\n\n最小结构测试。\n")
    write_text(target / "tests" / "test_workflow_structure.py", test_file())
    return ["tests/README.md", "tests/test_workflow_structure.py"]


def unit_result(unit_id: str, generated: list[str]) -> dict[str, Any]:
    return {
        "unit_id": unit_id,
        "status": "ok",
        "generated_files": [{"path": path} for path in generated],
        "generated": {
            "root_files": [path for path in generated if "/" not in path],
            "by_step": [{"step_slug": unit_id, "generated_files": [path for path in generated if "/" in path]}],
        },
        "handled_failures": [],
        "remaining_risks": [],
        "notes": ["runtime fake codex generated deterministic package files"],
    }


def implement_current_unit(output_path: pathlib.Path | None) -> dict[str, Any]:
    context_path = current_work_dir() / ".lgwf" / "current_implementation_unit_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8-sig"))
    unit = context["current_implementation_unit"]
    unit_id = unit["unit_id"]
    target = pathlib.Path(unit["target_package_abs"])

    if unit_id == "package_contracts":
        generated = write_package_contracts(target)
    elif unit_id == "root_workflow":
        generated = write_root_workflow(target)
    elif unit_id.startswith("stage_"):
        generated = write_stage(target, unit_id.removeprefix("stage_"))
    elif unit_id == "shared_helpers_tests":
        generated = write_support(target)
    else:
        generated = []

    result = unit_result(unit_id, generated)
    if output_path is not None:
        write_json(output_path, result)
    return result


def observe_result(output_path: pathlib.Path | None) -> dict[str, Any]:
    audit_path = current_work_dir() / ".lgwf" / "implementation_audit_result.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig")) if audit_path.exists() else {"passed": True}
    result = {
        "passed": audit.get("passed", True) is True,
        "failures": audit.get("failures", []),
        "checks": audit.get("checks", []),
        "audit": audit.get("audit", {}),
    }
    if output_path is not None:
        write_json(output_path, result)
    return result


def response_for(key: str, output_path: pathlib.Path | None) -> Any:
    if key.endswith("01_confirm_requirements/agents/propose_requirements_react.md"):
        payload = requirements_payload()
    elif key.endswith("02_confirm_business_flow/agents/propose_business_flow_react.md"):
        payload = business_flow_payload()
    elif key.endswith("03_confirm_step_designs/agents/design_steps_react.md"):
        payload = step_designs_payload()
    elif key.endswith("04_implement_steps_react/agents/reason.md"):
        text = "按已确认步骤设计拆分 package/root/stage/support units，并执行最小可 audit 实现。\n"
        if output_path is not None:
            write_text(output_path, text)
        return {"status": "ok", "summary": text}
    elif key.endswith("04_implement_steps_react/agents/act_unit.md"):
        return implement_current_unit(output_path)
    elif key.endswith("04_implement_steps_react/agents/observe.md"):
        return observe_result(output_path)
    else:
        payload = {
            "error": "unmatched fake codex prompt",
            "prompt_key": key,
        }
        if output_path is not None and output_path.suffix == ".json":
            write_json(output_path, payload)
        return payload

    if output_path is not None:
        write_json(output_path, payload)
    return payload


def main() -> int:
    prompt = extract_handoff_prompt(sys.argv)
    key = prompt_key(prompt)
    output_path = extract_output_path(prompt)
    log_call(key, output_path)
    payload = response_for(key, output_path)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if not (isinstance(payload, dict) and payload.get("error")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
'''.lstrip(),
        encoding="utf-8",
    )
    for name in ("codex.cmd", "codex.bat"):
        (fake_root / name).write_text(f'@echo off\r\n"{sys.executable}" "%~dp0fake_codex.py" %*\r\n', encoding="utf-8")


def prepare_temp_workspace(temp_root: Path) -> Path:
    (temp_root / ".git").mkdir()
    facade_target = temp_root / "skills" / "lgwf-wf-tools"
    vendor_target = facade_target / "vendor" / "lgwf-client-assist"
    shutil.copytree(VENDOR_ROOT, vendor_target)
    docs_target = facade_target / "docs"
    docs_target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        FACADE_ROOT / "docs" / "LGWF_WF_MODULAR_DEVELOPMENT.md",
        docs_target / "LGWF_WF_MODULAR_DEVELOPMENT.md",
    )
    share_target = facade_target / "workflows" / "01-share"
    share_target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(
        FACADE_ROOT / "workflows" / "01-share" / "module-contract.md",
        share_target / "module-contract.md",
    )
    return temp_root / "work"


@unittest.skipUnless(LGWF.exists(), f"LGWF runner not found: {LGWF}")
class LgwfWfCreateRuntimePackageE2ETest(unittest.TestCase):
    def test_runtime_fake_codex_creates_auditable_workflow_package(self) -> None:
        with ExitStack() as stack:
            temp_root = Path(runtime_temp_dir(stack))
            work_dir = prepare_temp_workspace(temp_root)
            fake_root = temp_root / "fake-codex"
            patch_root = temp_root / "pythonpath"
            input_file = temp_root / "input.json"
            output_file = temp_root / "final_state.json"
            work_dir.mkdir()
            write_fake_codex(fake_root)
            write_prompt_file_mode_patch(patch_root)
            write_json(
                input_file,
                {
                    "raw_intent": "创建一个用于 runtime E2E 的两阶段 LGWF workflow package。",
                    "constraints": ["目标 package 必须通过 lgwf authoring audit"],
                },
            )

            env = dict(os.environ)
            env["PATH"] = str(fake_root) + os.pathsep + env.get("PATH", "")
            env["PYTHONPATH"] = str(patch_root) + os.pathsep + env.get("PYTHONPATH", "")
            env["LGWF_FAKE_CODEX_PROMPT_FILE_MODE"] = "1"
            env["LGWF_FAKE_CODEX_ROOT_WORK_DIR"] = str(work_dir)
            env["LGWF_FAKE_CODEX_CALL_LOG"] = str(work_dir / ".lgwf" / "fake_codex_calls.jsonl")
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            completed = run_lgwf(
                [
                    "run",
                    "--workflow-lgwf",
                    str(WORKFLOW_LGWF),
                    "--work-dir",
                    str(work_dir),
                    "--input-json-file",
                    str(input_file),
                    "--auto-human",
                    "--rerun-existing",
                    "--output-json",
                    str(output_file),
                ],
                env=env,
                timeout=240,
            )

            diagnostic = "\n".join(
                [
                    f"STDOUT:\n{completed.stdout}",
                    f"STDERR:\n{completed.stderr}",
                    f"work_dir={work_dir}",
                    "FAKE_CODEX_CALLS:\n"
                    + (
                        (work_dir / ".lgwf" / "fake_codex_calls.jsonl").read_text(encoding="utf-8")
                        if (work_dir / ".lgwf" / "fake_codex_calls.jsonl").is_file()
                        else "<missing>"
                    ),
                ]
            )
            self.assertEqual(completed.returncode, 0, diagnostic)

            target_root = temp_root / TARGET_PACKAGE_ROOT
            self.assertTrue((target_root / "wf" / "workflow.lgwf").is_file(), diagnostic)
            self.assertTrue((target_root / "AGENTS.md").is_file(), diagnostic)
            self.assertTrue((target_root / "README.md").is_file(), diagnostic)
            for stage in STAGES:
                self.assertTrue((target_root / "wf" / stage / "workflow.lgwf").is_file(), stage)
                self.assertTrue((target_root / "wf" / stage / "agents").is_dir(), stage)
                self.assertTrue((target_root / "wf" / stage / "scripts").is_dir(), stage)
                self.assertTrue((target_root / "wf" / stage / "resources").is_dir(), stage)

            audit_result = read_json(work_dir / ".lgwf" / "implementation_audit_result.json")
            observe_result = read_json(work_dir / ".lgwf" / "implementation_observe.json")
            self.assertEqual(audit_result["status"], "passed")
            self.assertTrue(audit_result["passed"])
            self.assertTrue(audit_result["audit"]["ok"])
            self.assertEqual(audit_result["stage_dirs"], STAGES)
            self.assertTrue(observe_result["passed"])

            implementation = read_json(work_dir / ".lgwf" / "implementation_result.json")
            self.assertEqual(implementation["status"], "ok")
            self.assertEqual(implementation["target_package_root"], TARGET_PACKAGE_ROOT)
            self.assertEqual(implementation["unit_count"], 5)
            generated_paths = {item["path"] for item in implementation["generated_files"]}
            self.assertIn("wf/workflow.lgwf", generated_paths)
            self.assertIn("wf/01_collect_context/workflow.lgwf", generated_paths)
            self.assertIn("wf/02_run_checks/workflow.lgwf", generated_paths)

            summary = read_json(work_dir / ".lgwf" / "create_result_summary.json")
            self.assertEqual(summary["status"], "draft_structure_ready")
            self.assertEqual(summary["target_package_root"], TARGET_PACKAGE_ROOT)
            self.assertEqual(summary["implementation_audit"]["status"], "passed")
            self.assertTrue((work_dir / ".lgwf" / "post_fix_handoff_input.json").is_file())
            self.assertTrue((work_dir / ".lgwf" / "fake_codex_calls.jsonl").is_file())
            self.assertTrue(output_file.is_file(), diagnostic)


if __name__ == "__main__":
    unittest.main()
