from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    PACKAGE_ROOT
    / "wf"
    / "04_implement_steps_react"
    / "02_repair_implementation_react"
    / "03_observe_repair"
    / "scripts"
    / "audit_current_implementation.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("audit_current_implementation", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    old_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old_dont_write_bytecode
        shutil.rmtree(SCRIPT_PATH.parent / "__pycache__", ignore_errors=True)
    return module


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class AuditCurrentImplementationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def stage_dir(self, index: int, stage: str) -> str:
        return f"{index:02d}_{stage}"

    def make_work_dir(self, root: Path, stages: list[str]) -> Path:
        work_dir = root / "workflows" / "wf-create" / "ws"
        lgwf_dir = work_dir / ".lgwf"
        target_root = root / "skills" / "demo-workflow"
        (target_root / "wf").mkdir(parents=True)
        (target_root / "wf" / "workflow.lgwf").write_text("WORKFLOW demo;\nENTRY done;\n", encoding="utf-8")
        stage_manifest = [
            {
                "stage_id": stage,
                "stage_dir": self.stage_dir(index, stage),
                "workflow_ref": f"wf/{self.stage_dir(index, stage)}/workflow.lgwf",
            }
            for index, stage in enumerate(stages, start=1)
        ]
        create_dirs = [
            "wf",
            *[
                rel
                for item in stage_manifest
                for rel in (
                    f"wf/{item['stage_dir']}",
                    f"wf/{item['stage_dir']}/agents",
                    f"wf/{item['stage_dir']}/scripts",
                    f"wf/{item['stage_dir']}/resources",
                )
            ],
        ]
        create_files = [
            "AGENTS.md",
            "README.md",
            "entry_contract.json",
            "wf/artifact_contracts.json",
            "wf/workflow.lgwf",
            *[item["workflow_ref"] for item in stage_manifest],
        ]
        write_json(
            lgwf_dir / "implementation_context.json",
            {
                "workspace_root": str(root),
                "target_package_root": "skills/demo-workflow",
                "target_package_abs": str(target_root),
            },
        )
        write_json(
            lgwf_dir / "implementation_result.json",
            {
                "target_package_root": "skills/demo-workflow",
                "status": "implemented",
                "generated_files": [{"path": "README.md"}],
                "validation": [{"command": "unit", "status": "passed"}],
            },
        )
        write_json(
            lgwf_dir / "step_designs.json",
            {
                "confirmed": {
                    "target_package_root": "skills/demo-workflow",
                    "source_business_flow_stages": [{"stage_id": stage} for stage in stages],
                    "step_designs_proposal": [
                        {
                            "step_slug": "prepare",
                            "step_name": "准备",
                            "stage_id": "prepare",
                            "goal": "准备目标 workflow。",
                            "inputs": [".lgwf/create_requirements.json"],
                            "outputs": ["wf/01_prepare/workflow.lgwf"],
                            "dependencies": [],
                            "implementation_suggestions": ["生成阶段目录和 workflow。"],
                            "acceptance_notes": ["阶段 workflow 存在。"],
                            "out_of_scope": ["端到端运行保证"],
                            "confirmation_points": ["阶段边界正确"],
                            "target_files": create_files,
                            "target_dirs": create_dirs,
                        }
                    ],
                    "file_designs": [{"path": path} for path in create_files],
                    "directory_designs": [{"path": path} for path in create_dirs],
                }
            },
        )
        (target_root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
        (target_root / "README.md").write_text("# demo\n", encoding="utf-8")
        (target_root / "entry_contract.json").write_text("{}\n", encoding="utf-8")
        (target_root / "wf" / "artifact_contracts.json").write_text("{}\n", encoding="utf-8")
        return work_dir

    def add_stage(self, target_root: Path, stage: str) -> None:
        stage_root = target_root / "wf" / stage
        for rel in ("agents", "scripts", "resources"):
            (stage_root / rel).mkdir(parents=True, exist_ok=True)
        (stage_root / "workflow.lgwf").write_text("WORKFLOW stage;\nENTRY done;\n", encoding="utf-8")

    def patch_authoring_audit(self, ok: bool = True) -> None:
        self.module.run_authoring_audit = lambda workflow_lgwf, workspace_root: {
            "ok": ok,
            "skipped": False,
            "exit_code": 0 if ok else 1,
            "stdout": "",
            "stderr": "" if ok else "audit failed",
        }

    def test_audit_current_implementation_collects_all_workflow_audit_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare", "finish"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            self.add_stage(target_root, "02_finish")

            def audit_each(workflow_lgwf: Path, workspace_root: Path) -> dict[str, object]:
                rel_path = workflow_lgwf.resolve().relative_to(target_root.resolve()).as_posix()
                ok = rel_path == "wf/workflow.lgwf"
                return {
                    "ok": ok,
                    "skipped": False,
                    "exit_code": 0 if ok else 2,
                    "stdout": "",
                    "stderr": "" if ok else f"DSLParseError: {rel_path}:1:12: Expected ';'.",
                }

            self.module.run_authoring_audit = audit_each

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(result["needs_post_fix"])
            failed_workflow_paths = [
                item["package_relative_path"]
                for item in result["workflow_audits"]
                if not item["ok"]
            ]
            self.assertEqual(
                failed_workflow_paths,
                ["wf/01_prepare/workflow.lgwf", "wf/02_finish/workflow.lgwf"],
            )
            self.assertTrue(any("wf/01_prepare/workflow.lgwf" in item for item in result["failures"]))
            self.assertTrue(any("wf/02_finish/workflow.lgwf" in item for item in result["failures"]))

    def test_run_authoring_audit_uses_lgwf_dsl_cli_tool(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflow_lgwf = root / "skills" / "demo" / "wf" / "workflow.lgwf"
            workflow_lgwf.parent.mkdir(parents=True)
            workflow_lgwf.write_text("WORKFLOW demo;\nENTRY done;\n", encoding="utf-8")
            calls = []

            lgwf_client = types.ModuleType("lgwf_client")
            lgwf_client_tools = types.ModuleType("lgwf_client.tools")
            registry = types.ModuleType("lgwf_client.tools.registry")

            def run_builtin_tool(name: str, options: dict[str, object], workspace_root: Path) -> dict[str, object]:
                calls.append((name, options, workspace_root))
                return {
                    "passed": True,
                    "exit_code": 0,
                    "stdout": "{}\n",
                    "stderr": "",
                    "payload": {},
                    "diagnostics": [],
                }

            registry.run_builtin_tool = run_builtin_tool
            lgwf_client.tools = lgwf_client_tools
            lgwf_client_tools.registry = registry
            old_modules = {
                key: sys.modules.get(key)
                for key in ("lgwf_client", "lgwf_client.tools", "lgwf_client.tools.registry")
            }
            sys.modules["lgwf_client"] = lgwf_client
            sys.modules["lgwf_client.tools"] = lgwf_client_tools
            sys.modules["lgwf_client.tools.registry"] = registry
            try:
                result = self.module.run_authoring_audit(workflow_lgwf, root)
            finally:
                for key, module in old_modules.items():
                    if module is None:
                        sys.modules.pop(key, None)
                    else:
                        sys.modules[key] = module

            self.assertTrue(result["ok"])
            self.assertEqual(calls[0][0], "lgwf_dsl_cli")
            self.assertEqual(calls[0][1]["command"], "audit")
            self.assertEqual(calls[0][1]["input"], "skills/demo/wf/workflow.lgwf")
            self.assertEqual(calls[0][2], root.resolve())

    def test_audit_current_implementation_accepts_confirmed_stage_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare", "finish"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            self.add_stage(target_root, "02_finish")
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertTrue(result["passed"])
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["stage_ids"], ["prepare", "finish"])
            self.assertEqual(result["stage_dirs"], ["01_prepare", "02_finish"])
            self.assertTrue((work_dir / ".lgwf" / "implementation_audit_result.json").exists())
            self.assertTrue((work_dir / ".lgwf" / "implementation_observe.json").exists())

    def test_audit_current_implementation_reports_missing_confirmed_stage_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            for rel in ("agents", "scripts", "resources"):
                (target_root / "wf" / "01_prepare" / rel).mkdir(parents=True, exist_ok=True)
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(
                any("step_designs file_design wf/01_prepare/workflow.lgwf" in item for item in result["failures"])
            )

    def test_audit_current_implementation_reports_missing_stage_private_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            stage_root = root / "skills" / "demo-workflow" / "wf" / "01_prepare"
            stage_root.mkdir(parents=True)
            (stage_root / "workflow.lgwf").write_text("WORKFLOW stage;\nENTRY done;\n", encoding="utf-8")
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("step_designs directory_design wf/01_prepare/agents" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_missing_generated_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            (target_root / "README.md").unlink()
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("implementation_result generated file README.md" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_failed_implementation_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            write_json(
                work_dir / ".lgwf" / "implementation_result.json",
                {
                    "target_package_root": "skills/demo-workflow",
                    "status": "failed",
                    "generated_files": [{"path": "README.md"}],
                    "failed_units": ["stage_01_prepare"],
                    "remaining_risks": ["unit failed"],
                    "validation": [{"command": "unit", "status": "passed"}],
                },
            )
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("implementation_result 自报状态未通过" in item for item in result["failures"]))
            self.assertTrue(any("stage_01_prepare" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_missing_confirmed_file_design(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            step_designs = json.loads((work_dir / ".lgwf" / "step_designs.json").read_text(encoding="utf-8"))
            step_designs["confirmed"]["file_designs"] = [
                {"path": "wf/01_prepare/scripts/prepare_context.py"}
            ]
            step_designs["confirmed"]["step_designs_proposal"][0]["target_files"] = [
                "wf/01_prepare/scripts/prepare_context.py"
            ]
            write_json(work_dir / ".lgwf" / "step_designs.json", step_designs)
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("step_designs file_design wf/01_prepare/scripts/prepare_context.py" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_latest_invalid_repair_round(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            write_json(
                work_dir / ".lgwf" / "implementation_result.json",
                {
                    "target_package_root": "skills/demo-workflow",
                    "status": "implemented",
                    "generated_files": [{"path": "README.md"}],
                    "validation": [{"command": "unit", "status": "passed"}],
                    "repair_rounds": [
                        {
                            "status": "invalid_plan",
                            "failures": ["repair generated files outside target_files: ['README.md']"],
                        }
                    ],
                },
            )
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("repair_round invalid_plan" in item for item in result["failures"]))

    def test_audit_current_implementation_accepts_repo_relative_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            write_json(
                work_dir / ".lgwf" / "implementation_result.json",
                {
                    "target_package_root": "skills/demo-workflow",
                    "status": "implemented",
                    "generated_files": [
                        {"path": "skills/demo-workflow/README.md"},
                        {"path": "skills/demo-workflow/wf/workflow.lgwf"},
                    ],
                    "validation": [{"command": "unit", "status": "passed"}],
                },
            )
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertTrue(result["passed"])

    def test_audit_current_implementation_reports_agent_loop_target_dirs_prompt_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            (target_root / "wf" / "01_prepare" / "workflow.lgwf").write_text(
                "WORKFLOW stage;\nENTRY loop;\nAGENT_LOOP loop MAX_ITERATIONS 1 ARTIFACTS \"x\" STATUS state.s REPORT state.r { OBSERVE PY o SCRIPT \"scripts/o.py\" RESULT state.o; DIAGNOSE CODEX d PROMPT_REF \"agents/d.md\" RESULT state.d; PLAN CODEX p PROMPT_REF \"agents/p.md\" RESULT state.p; ACT CODEX a PROMPT_REF \"agents/a.md\" RESULT state.a; VERIFY PY v SCRIPT \"scripts/v.py\" RESULT state.v; DECIDE PY c SCRIPT \"scripts/c.py\" RESULT state.c; };\n",
                encoding="utf-8",
            )
            (target_root / "wf" / "01_prepare" / "agents" / "d.md").write_text(
                "只能修改 TARGET_DIRS 指向的目录。\n",
                encoding="utf-8",
            )
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("AGENT_LOOP 阶段文档不得承诺 TARGET_DIRS" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_runtime_pollution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            (target_root / ".lgwf").mkdir()
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("目标 package 不得包含运行态目录" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_missing_workflow_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            (target_root / "wf" / "01_prepare" / "workflow.lgwf").write_text(
                'WORKFLOW stage;\nENTRY act;\nCODEX act\n  PROMPT "agents/missing.md"\n  OUTPUT_JSON ".lgwf/out.json" AS_FILE;\n',
                encoding="utf-8",
            )
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("PROMPT 引用文件不存在" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            (target_root / "README.md").write_bytes(b"\xef\xbb\xbf# demo\n")
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("文本文件不得包含 UTF-8 BOM" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_placeholder_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            (target_root / "README.md").write_text("<!-- LGWF_PLACEHOLDER: README.md -->\n", encoding="utf-8")
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("仍包含占位内容" in item for item in result["failures"]))

    def test_audit_current_implementation_reports_exact_content_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            step_designs = json.loads((work_dir / ".lgwf" / "step_designs.json").read_text(encoding="utf-8"))
            for item in step_designs["confirmed"]["file_designs"]:
                if item.get("path") == "README.md":
                    item["content_mode"] = "exact"
                    item["exact_content"] = "# expected\n"
            write_json(work_dir / ".lgwf" / "step_designs.json", step_designs)
            (target_root / "README.md").write_text("# actual\n", encoding="utf-8")
            self.patch_authoring_audit()

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(any("exact 文件内容与 step_designs" in item for item in result["failures"]))

    def test_audit_current_implementation_marks_authoring_audit_failure_as_repair_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work_dir = self.make_work_dir(root, ["prepare"])
            target_root = root / "skills" / "demo-workflow"
            self.add_stage(target_root, "01_prepare")
            self.patch_authoring_audit(ok=False)

            result = self.module.audit_current_implementation(work_dir)

            self.assertFalse(result["passed"])
            self.assertTrue(result["needs_post_fix"])
            self.assertIn("lgwf_dsl_cli audit 未通过", result["failures"])


if __name__ == "__main__":
    unittest.main()
