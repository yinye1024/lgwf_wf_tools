from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
MODULE_COUNTER = 0
FORBIDDEN_RUNTIME_TOKENS = (
    "lgwf.py run",
    "--workflow-lgwf",
    "codex",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
)


def load_script_module(relative_path: str) -> types.ModuleType:
    global MODULE_COUNTER
    MODULE_COUNTER += 1
    module_path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(f"wf_script_flow_module_{MODULE_COUNTER}", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载脚本模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def isolated_workdir() -> Path:
    previous = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        os.chdir(workdir)
        try:
            yield workdir
        finally:
            os.chdir(previous)


def write_utf8_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def runtime_guard_and_capture_stdout_json(main_callable) -> dict:
    def fail_runtime(*args, **kwargs):
        raise AssertionError("脚本级 E2E 禁止启动 runtime、外部命令或真实 Codex")

    stdout = io.StringIO()
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("subprocess.run", side_effect=fail_runtime))
        stack.enter_context(mock.patch("subprocess.Popen", side_effect=fail_runtime))
        stack.enter_context(mock.patch("os.system", side_effect=fail_runtime))
        stack.enter_context(contextlib.redirect_stdout(stdout))
        main_callable()
    return json.loads(stdout.getvalue())


def assert_workflow_route_text(testcase: unittest.TestCase, expected_text: str) -> None:
    workflow_path = PACKAGE_ROOT / "wf/04_confirm_business_flow/workflow.lgwf"
    workflow_text = workflow_path.read_text(encoding="utf-8")
    testcase.assertIn(expected_text, workflow_text)


def make_prompt_source_tree(root: Path) -> Path:
    source_root = root / "sample_prompt_workflow"
    (source_root / "flow" / "agents").mkdir(parents=True)
    (source_root / "flow" / "workflow.lgwf").write_text("WORKFLOW demo;\n", encoding="utf-8")
    (source_root / "flow" / "agents" / "inspect.md").write_text("# inspect\n", encoding="utf-8")
    (source_root / "flow" / "notes.txt").write_text("notes\n", encoding="utf-8")
    (source_root / "flow" / "definition.prompt").write_text("prompt\n", encoding="utf-8")
    (source_root / "flow" / "config.json").write_text("{\"ok\":true}\n", encoding="utf-8")
    (source_root / "flow" / "vars.yaml").write_text("key: value\n", encoding="utf-8")
    (source_root / ".lgwf").mkdir()
    (source_root / ".lgwf" / "hidden.md").write_text("skip\n", encoding="utf-8")
    (source_root / "__pycache__").mkdir()
    (source_root / "__pycache__" / "skip.txt").write_text("skip\n", encoding="utf-8")
    (source_root / "node_modules").mkdir()
    (source_root / "node_modules" / "skip.md").write_text("skip\n", encoding="utf-8")
    (source_root / ".git").mkdir()
    (source_root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (source_root / "binary.bin").write_bytes(b"\x00\x01")
    return source_root


def make_full_proposal(*, target_package_root: str = "skills/lgwf-wf-tools/workflows/generated") -> dict:
    return {
        "workflow_name": "wf-convert-target",
        "target_package_root": target_package_root,
        "raw_intent": "把现有 prompt workflow 转成 LGWF workflow",
        "source_root": "samples/source-flow",
        "stages": [{"id": "discover", "summary": "解析输入"}],
        "prompt_contracts": [{"file": "agents/inspect.md", "purpose": "分析源流程"}],
        "source_business_contract": {},
        "prompt_execution_mechanics": [],
        "presentation_constraints": [],
        "discarded_prompt_techniques": [],
        "conversion_mapping": [],
        "parity_requirements": [],
        "human_approval_points": ["confirm_create_input"],
        "assumptions": ["源目录可读"],
        "out_of_scope": ["真实 runtime 验证"],
        "run_workflow_notes_for_wf_create_fast": ["交给 wf-create-fast 继续生成"],
    }


class ScriptFlowE2ETests(unittest.TestCase):
    def test_case_index_prompt_files_bootstrap_inventory(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/index_prompt_files.py")
        with isolated_workdir() as workdir:
            source_root = make_prompt_source_tree(workdir)
            write_utf8_json(
                workdir / ".lgwf" / "prompt_convert_target.json",
                {
                    "target_dir": str(source_root),
                    "entry_files": ["flow/workflow.lgwf"],
                    "target_workflow_name": "demo",
                    "target_package_root": "samples/demo",
                    "constraints": ["utf-8"],
                },
            )

            result = runtime_guard_and_capture_stdout_json(module.main)
            inventory = json.loads((workdir / ".lgwf" / "prompt_file_index.json").read_text(encoding="utf-8"))

            self.assertEqual(result["lgwf_wf_convert.prompt_file_index"], inventory)
            self.assertEqual(inventory["root"], str(source_root.resolve()))
            files = inventory["files"]
            file_paths = {item["path"] for item in files}
            allowed_suffixes = {".md", ".txt", ".prompt", ".json", ".yaml", ".yml", ".lgwf"}
            self.assertTrue(all(Path(item["path"]).suffix in allowed_suffixes for item in files))
            self.assertIn("flow/workflow.lgwf", file_paths)
            self.assertIn("flow/agents/inspect.md", file_paths)
            self.assertIn("flow/notes.txt", file_paths)
            self.assertIn("flow/definition.prompt", file_paths)
            self.assertNotIn(".lgwf/hidden.md", file_paths)
            self.assertFalse(any(path.startswith(".lgwf/") for path in file_paths))
            self.assertFalse(any(path.startswith("__pycache__/") for path in file_paths))
            self.assertFalse(any(path.startswith("node_modules/") for path in file_paths))
            self.assertFalse(any(path.startswith(".git/") for path in file_paths))
            self.assertEqual(inventory["workflow_files"], ["flow/workflow.lgwf"])
            self.assertCountEqual(
                inventory["prompt_candidates"],
                ["flow/agents/inspect.md", "flow/notes.txt", "flow/definition.prompt"],
            )
            for name in ("prompt_workflow_inspection_observe.json", "wf_create_fast_input_observe.json"):
                placeholder = json.loads((workdir / ".lgwf" / name).read_text(encoding="utf-8"))
                self.assertEqual(placeholder, {"verdict": "initial", "issues": []})
            proposal_placeholder = json.loads(
                (workdir / ".lgwf" / "wf_create_fast_input_proposal.json").read_text(encoding="utf-8")
            )
            self.assertEqual(proposal_placeholder, {})

    def test_case_decide_inspection_continue_on_gap(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_inspection.py")
        with isolated_workdir() as workdir:
            write_utf8_json(workdir / ".lgwf" / "prompt_workflow_inspection.json", {"source_summary": ["only"]})
            write_utf8_json(
                workdir / ".lgwf" / "prompt_workflow_inspection_observe.json",
                {"verdict": "revise", "issues": ["字段不完整"]},
            )

            result = runtime_guard_and_capture_stdout_json(module.main)

            self.assertEqual(result, {"next": "continue"})

    def test_case_decide_inspection_exit_on_pass(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_inspection.py")
        with isolated_workdir() as workdir:
            write_utf8_json(
                workdir / ".lgwf" / "prompt_workflow_inspection.json",
                {
                    "source_summary": ["summary"],
                    "detected_stages": [{"id": "stage-1"}],
                    "prompt_contracts": [{"name": "contract"}],
                },
            )
            write_utf8_json(
                workdir / ".lgwf" / "prompt_workflow_inspection_observe.json",
                {"verdict": "pass", "issues": []},
            )

            result = runtime_guard_and_capture_stdout_json(module.main)

            self.assertEqual(result, {"next": "exit"})

    def test_case_decide_create_input_continue_on_gap(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_create_input.py")
        with isolated_workdir() as workdir:
            write_utf8_json(workdir / ".lgwf" / "wf_create_fast_input_proposal.json", {"workflow_name": "wf"})
            write_utf8_json(
                workdir / ".lgwf" / "wf_create_fast_input_observe.json",
                {"verdict": "revise", "issues": ["缺少字段"]},
            )

            result = runtime_guard_and_capture_stdout_json(module.main)

            self.assertEqual(result, {"next": "continue"})

    def test_case_decide_create_input_continue_on_blocking_issue(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_create_input.py")
        with isolated_workdir() as workdir:
            write_utf8_json(
                workdir / ".lgwf" / "wf_create_fast_input_proposal.json",
                make_full_proposal(target_package_root="skills/lgwf-wf-tools/workflows/generated"),
            )
            write_utf8_json(
                workdir / ".lgwf" / "wf_create_fast_input_observe.json",
                {
                    "verdict": "revise",
                    "issues": [
                        {
                            "field": "stages",
                            "blocking": True,
                            "issue": "缺少 evidence_strength，approval 无法原样确认",
                            "required_change": "为每个 stage 补充 evidence_strength",
                            "severity": "high",
                        }
                    ],
                },
            )

            result = runtime_guard_and_capture_stdout_json(module.main)

            self.assertEqual(result, {"next": "continue"})

    def test_case_decide_create_input_exit_on_non_blocking_issue(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_create_input.py")
        with isolated_workdir() as workdir:
            write_utf8_json(
                workdir / ".lgwf" / "wf_create_fast_input_proposal.json",
                make_full_proposal(target_package_root="skills/lgwf-wf-tools/workflows/generated"),
            )
            write_utf8_json(
                workdir / ".lgwf" / "wf_create_fast_input_observe.json",
                {
                    "verdict": "revise",
                    "issues": [
                        {
                            "field": "run_workflow_notes_for_wf_create_fast",
                            "blocking": False,
                            "issue": "建议在人工确认时关注剩余上下文",
                            "required_change": "交给 confirm_create_input 人工确认",
                            "severity": "low",
                        }
                    ],
                },
            )

            result = runtime_guard_and_capture_stdout_json(module.main)

            self.assertEqual(result, {"next": "exit"})

    def test_case_decide_create_input_allows_absolute_source_root(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_create_input.py")
        with isolated_workdir() as workdir:
            proposal = make_full_proposal(target_package_root="skills/lgwf-wf-tools/workflows/generated")
            proposal["source_root"] = str((workdir / "source_prompt_workflow").resolve())
            write_utf8_json(workdir / ".lgwf" / "wf_create_fast_input_proposal.json", proposal)
            write_utf8_json(
                workdir / ".lgwf" / "wf_create_fast_input_observe.json",
                {"verdict": "pass", "issues": []},
            )

            result = runtime_guard_and_capture_stdout_json(module.main)

            self.assertEqual(result, {"next": "exit"})

    def test_case_decide_create_input_exit_on_pass(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/decide_create_input.py")
        with isolated_workdir() as workdir:
            write_utf8_json(
                workdir / ".lgwf" / "wf_create_fast_input_proposal.json",
                make_full_proposal(target_package_root="skills/lgwf-wf-tools/workflows/generated"),
            )
            write_utf8_json(
                workdir / ".lgwf" / "wf_create_fast_input_observe.json",
                {"verdict": "pass", "issues": []},
            )

            result = runtime_guard_and_capture_stdout_json(module.main)

            self.assertEqual(result, {"next": "exit"})

    def test_case_confirm_create_input_approve_route_and_finalize(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/finalize_create_input.py")
        with isolated_workdir() as workdir:
            proposal = make_full_proposal()
            write_utf8_json(workdir / ".lgwf" / "wf_create_fast_input_proposal.json", proposal)

            result = runtime_guard_and_capture_stdout_json(module.main)

            assert_workflow_route_text(self, 'WHEN "approve" THEN finalize_create_input')
            finalize_result = result["lgwf_wf_convert.finalize_create_input_result"]
            self.assertEqual(finalize_result["decision"], "approve")
            self.assertEqual(finalize_result["proposal_path"], ".lgwf/wf_create_fast_input_proposal.json")
            self.assertEqual(finalize_result["confirmed_path"], ".lgwf/wf_create_fast_input.json")
            confirmed = json.loads((workdir / ".lgwf" / "wf_create_fast_input.json").read_text(encoding="utf-8"))
            self.assertEqual(confirmed["workflow_name"], proposal["workflow_name"])
            self.assertEqual(confirmed["raw_intent"], proposal["raw_intent"])
            self.assertFalse((workdir / ".lgwf" / "wf_create_fast_payload.json").exists())

    def test_case_confirm_create_input_revise_reject_route_contract(self):
        module = load_script_module("wf/04_confirm_business_flow/scripts/finalize_create_input.py")
        assert_workflow_route_text(self, 'WHEN "revise" THEN propose_create_input_react')
        assert_workflow_route_text(self, 'WHEN "reject" THEN FAIL_ALL')
        with isolated_workdir():
            with self.assertRaisesRegex(FileNotFoundError, "wf_create_fast_input_proposal"):
                module.main()

    def test_case_prepare_wf_create_fast_payload_confirmed_input(self):
        module = load_script_module("wf/07_prepare_wf_create_fast_payload/scripts/prepare_wf_create_fast_payload.py")
        with isolated_workdir() as workdir:
            confirmed = make_full_proposal(target_package_root="C:/Users/Administrator/Desktop/tmp3/lgwf_wf")
            confirmed["workflow_name"] = "confirmed-workflow"
            confirmed["raw_intent"] = "使用 confirmed 输入"
            write_utf8_json(workdir / ".lgwf" / "wf_create_fast_input.json", confirmed)

            confirmed_result = runtime_guard_and_capture_stdout_json(module.main)
            handoff_target = json.loads((workdir / ".lgwf" / "wf_create_fast_handoff.json").read_text(encoding="utf-8"))
            handoff_state = confirmed_result["lgwf_wf_convert.wf_create_fast_handoff_payload"]
            self.assertEqual(
                handoff_target["workflow_name"],
                "confirmed-workflow",
            )
            self.assertEqual(
                handoff_target["target_package_root"],
                "C:\\Users\\Administrator\\Desktop\\tmp3\\lgwf_wf",
            )
            self.assertEqual(handoff_target["raw_intent"], "使用 confirmed 输入")
            self.assertNotIn("source_root", handoff_target)
            self.assertNotIn("request", handoff_target)
            self.assertEqual(
                handoff_state["wf_create_fast_launch_input"]["request"]["target_file"],
                str((workdir / ".lgwf" / "wf_create_fast_handoff.json").resolve()),
            )
            launch_input_path = workdir / ".lgwf" / "wf_create_fast_launch_input.json"
            launch_input = json.loads(launch_input_path.read_text(encoding="utf-8"))
            self.assertEqual(
                launch_input,
                handoff_state["wf_create_fast_launch_input"],
            )
            self.assertEqual(handoff_state["input_json_file"], str(launch_input_path.resolve()))
            self.assertEqual(handoff_state["workflow_lgwf"], "workflows/wf-create-fast/wf/workflow.lgwf")
            self.assertEqual(handoff_state["work_dir"], "workflows/wf-create-fast/ws")
            self.assertIn("wf_create_fast_launch_input.json", handoff_state["suggested_command"])
            self.assertTrue(handoff_state["handoff_ack_required"])
            self.assertTrue((workdir / ".lgwf" / "wf_create_fast_handoff.json").exists())
            self.assertTrue(launch_input_path.exists())
            self.assertFalse((workdir / ".lgwf" / "wf_create_fast_payload.json").exists())
            self.assertFalse((workdir / ".lgwf" / "wf_create_fast_input_for_wf_create_fast.json").exists())

    def test_case_prepare_wf_create_fast_payload_requires_finalized_input(self):
        module = load_script_module("wf/07_prepare_wf_create_fast_payload/scripts/prepare_wf_create_fast_payload.py")
        with isolated_workdir() as workdir:
            write_utf8_json(workdir / ".lgwf" / "wf_create_fast_input_proposal.json", make_full_proposal())
            with self.assertRaisesRegex(FileNotFoundError, "wf_create_fast_input.json"):
                module.main()

    def test_case_prepare_wf_create_fast_payload_path_guardrails(self):
        module = load_script_module("wf/07_prepare_wf_create_fast_payload/scripts/prepare_wf_create_fast_payload.py")
        for raw_path in (".", "../outside", "inside/.lgwf/state", "https://example.com/workflow"):
            with self.subTest(target_package_root=raw_path):
                with self.assertRaises(ValueError):
                    module.normalize_package_path(raw_path, "target_package_root")
        for raw_path in ("/absolute/path", "C:/absolute/path", "skills/example"):
            with self.subTest(target_package_root=raw_path):
                normalized = module.normalize_package_path(raw_path, "target_package_root")
                self.assertEqual(normalized.replace("\\", "/"), raw_path)

        with isolated_workdir() as workdir:
            proposal = make_full_proposal(target_package_root="../outside")
            write_utf8_json(workdir / ".lgwf" / "wf_create_fast_input.json", proposal)
            with self.assertRaises(ValueError):
                module.main()
            self.assertFalse((workdir / ".lgwf" / "wf_create_fast_payload.json").exists())
            self.assertFalse((workdir / ".lgwf" / "wf_create_fast_handoff.json").exists())

    def test_guard_markers_document_forbidden_runtime_patterns(self):
        guard_source = (PACKAGE_ROOT / "tests" / "test_wf_script_flow_e2e.py").read_text(encoding="utf-8")
        for token in FORBIDDEN_RUNTIME_TOKENS:
            self.assertIn(token, guard_source)


if __name__ == "__main__":
    unittest.main()
