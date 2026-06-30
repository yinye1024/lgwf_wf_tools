from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


class pushd:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous = Path.cwd()

    def __enter__(self) -> None:
        os.chdir(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:
        os.chdir(self.previous)


def load_module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def call_main(relative: str, cwd: Path, name: str) -> str:
    module = load_module(relative, name)
    output = StringIO()
    with pushd(cwd), redirect_stdout(output):
        module.main()
    return output.getvalue()


def create_target_workflow(root: Path) -> Path:
    workflow = root / "workflow.lgwf"
    workflow.write_text(
        """WORKFLOW sample_target;
ENTRY prepare;

PY prepare
  SCRIPT "scripts/prepare.py"
  RESULT state.sample.prepare
  UPDATES_STATE;

CODEX generate_json
  PROMPT "agents/generate.md"
  OUTPUT_JSON ".lgwf/generated.json"
  RESULT state.sample.generate;

APPROVAL confirm
  PROMPT "confirm"
  READ state.sample.confirm_context
  WRITE state.sample.confirm
  RESULT state.sample.confirm_result
  PERSIST ".lgwf/confirm.json"
  POLL 1;

REACT repair_loop MAX 2
  SPEC "agents/spec.md"
  REASON CODEX
    PROMPT "agents/reason.md"
    RESULT state.sample.reason
  ACT CODEX
    PROMPT "agents/act.md"
    OUTPUT_JSON ".lgwf/act.json"
    RESULT state.sample.act
  OBSERVE CODEX
    PROMPT "agents/observe.md"
    OUTPUT_JSON ".lgwf/observe.json"
    RESULT state.sample.observe
  DECIDE PY
    SCRIPT "scripts/decide.py"
    RESULT state.sample.decide
    UPDATES_STATE;

ROUTE choose_next
  WHEN "retry" THEN repair_loop
  WHEN "done" THEN finish;

PY finish
  SCRIPT "scripts/finish.py"
  RESULT state.sample.finish;

FLOW prepare
  THEN generate_json
  THEN confirm
  THEN repair_loop
  THEN choose_next;
""",
        encoding="utf-8",
    )
    (root / "scripts").mkdir()
    (root / "scripts" / "prepare.py").write_text("print('{}')\n", encoding="utf-8")
    (root / "scripts" / "decide.py").write_text("print('{\"next\":\"exit\"}')\n", encoding="utf-8")
    (root / "scripts" / "finish.py").write_text("print('{}')\n", encoding="utf-8")
    (root / "agents").mkdir()
    for name in ("generate.md", "spec.md", "reason.md", "act.md", "observe.md"):
        (root / "agents" / name).write_text(f"# {name}\nOUTPUT_JSON\n", encoding="utf-8")
    return workflow


class E2eGeneratorScriptsTest(unittest.TestCase):
    def test_validate_target_request_requires_workflow_lgwf(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            write_json(work / ".lgwf" / "e2e_target_request.json", {})
            with self.assertRaisesRegex(SystemExit, "workflow_lgwf is required"):
                call_main("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", work, "validate_missing")

    def test_validate_target_request_defaults_generated_test_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            workflow = create_target_workflow(target)
            write_json(work / ".lgwf" / "e2e_target_request.json", {"workflow_lgwf": workflow.as_posix()})

            call_main("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", work, "validate_defaults")

            normalized = read_json(work / ".lgwf" / "e2e_target_request.normalized.json")
            self.assertEqual(normalized["test_output_dir"], "tests")
            self.assertEqual(normalized["test_name_prefix"], "sample_target")
            self.assertEqual(normalized["generated_tests"]["script_flow"], "test_sample_target_script_flow_e2e.py")
            self.assertNotIn("real_codex_env", normalized)

    def test_parse_workflow_graph_covers_core_node_types_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            workflow = create_target_workflow(target)
            write_json(work / ".lgwf" / "e2e_target_request.json", {"workflow_lgwf": workflow.as_posix()})

            call_main("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", work, "validate_parse")
            call_main("01_inspect_target/02_scan_workflow_package/scripts/scan_workflow_package.py", work, "scan_parse")
            call_main("01_inspect_target/03_parse_workflow_graph/scripts/parse_workflow_graph.py", work, "parse_graph")

            graph = read_json(work / ".lgwf" / "e2e_workflow_graph.json")
            kinds = {node["kind"] for node in graph["nodes"]}
            self.assertTrue({"PY", "CODEX", "APPROVAL", "REACT", "ROUTE"}.issubset(kinds))
            self.assertIn(".lgwf/generated.json", graph["output_json"])
            self.assertIn(".lgwf/confirm.json", graph["persist"])
            self.assertEqual(graph["routes"][0]["branches"][0]["value"], "retry")

    def test_coverage_matrix_extracts_routes_approvals_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            workflow = create_target_workflow(target)
            write_json(work / ".lgwf" / "e2e_target_request.json", {"workflow_lgwf": workflow.as_posix()})

            for relative, name in (
                ("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", "validate_cov"),
                ("01_inspect_target/02_scan_workflow_package/scripts/scan_workflow_package.py", "scan_cov"),
                ("01_inspect_target/03_parse_workflow_graph/scripts/parse_workflow_graph.py", "parse_cov"),
                ("02_derive_coverage_matrix/01_build_coverage_matrix/scripts/build_coverage_matrix.py", "coverage"),
            ):
                call_main(relative, work, name)

            matrix = read_json(work / ".lgwf" / "e2e_coverage_matrix.json")
            self.assertEqual(matrix["target"]["generated_tests"]["runtime_fake"], "test_sample_target_runtime_fake_e2e.py")
            self.assertEqual({route["value"] for route in matrix["script_flow"]["routes"]}, {"retry", "done"})
            self.assertIn(".lgwf/confirm.json", matrix["script_flow"]["approval_persist"])
            self.assertIn(".lgwf/generated.json", matrix["runtime_fake"]["output_json"])
            self.assertEqual({route["value"] for route in matrix["runtime_fake"]["routes"]}, {"retry", "done"})
            self.assertEqual(matrix["runtime_fake"]["persist_artifacts"], [".lgwf/confirm.json"])
            self.assertTrue(matrix["runtime_fake"]["flows"])
            self.assertFalse(matrix["real_positive"]["discover_collected"])
            self.assertEqual(
                matrix["real_positive"]["manual_run_command"],
                "python tests/test_sample_target_real_positive_e2e.py",
            )
            self.assertIn(
                {"route_id": "choose_next", "value": "retry", "target": "repair_loop", "workflow": "workflow.lgwf"},
                matrix["runtime_fake"]["branch_targets"],
            )
            self.assertIn(
                {"route_id": "choose_next", "value": "done", "target": "finish", "workflow": "workflow.lgwf"},
                matrix["runtime_fake"]["branch_targets"],
            )
            repair_ids = {item["id"] for item in matrix["runtime_fake"]["repair_or_retry_nodes"]}
            self.assertIn("repair_loop", repair_ids)

    def test_runtime_fake_prompts_require_scenario_coverage_schema(self) -> None:
        spec = (ROOT / "04_runtime_fake_e2e" / "01_design" / "agents" / "spec.md").read_text(encoding="utf-8")
        design = (ROOT / "04_runtime_fake_e2e" / "01_design" / "agents" / "reason.md").read_text(encoding="utf-8")
        generate = (ROOT / "04_runtime_fake_e2e" / "02_generate" / "agents" / "act.md").read_text(encoding="utf-8")
        observe = (ROOT / "04_runtime_fake_e2e" / "03_validate" / "agents" / "observe.md").read_text(encoding="utf-8")
        workflow = (ROOT / "04_runtime_fake_e2e" / "workflow.lgwf").read_text(encoding="utf-8")

        for token in (
            "scenarios[]",
            "happy_path",
            "manual_approval_required",
            "expected_runtime_path",
            "approval_decisions",
            "covered_branches",
            "coverage_gaps[]",
            "history_count",
            "不会回到错误的前序 Codex repair loop",
        ):
            self.assertIn(token, spec)
        for token in ("scenarios[]", "scenario_id", "triggered_branches"):
            self.assertIn(token, design)
        self.assertIn("happy_path", design)
        self.assertIn("scenario_generation[]", generate)
        self.assertIn("test_<scenario_id>", generate)
        self.assertIn("call_index", generate)
        self.assertIn("e2e_runtime_fake_repair_context.json", design)
        self.assertIn("e2e_runtime_fake_observe.json", design)
        self.assertIn("repair_plan[]", design)
        self.assertIn("e2e_runtime_fake_repair_context.json", generate)
        self.assertIn("applied_repairs[]", generate)
        self.assertIn("scenario_checks", observe)
        self.assertIn("coverage_gaps", observe)
        self.assertIn("business_route_coverage", observe)
        self.assertIn("manual_approval_required", observe)
        self.assertIn("issue_code", observe)
        self.assertIn("prepare_runtime_fake_repair_context", workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/e2e_runtime_fake_repair_context.json"', workflow)
        self.assertIn('CONTEXT workspace file ".lgwf/e2e_runtime_fake_observe.json"', workflow)

    def test_react_reason_prompts_receive_observe_feedback(self) -> None:
        contracts = (
            (
                "03_script_flow_e2e",
                "prepare_script_flow_observe_feedback",
                ".lgwf/e2e_script_flow_observe.json",
            ),
            (
                "04_runtime_fake_e2e",
                "prepare_runtime_fake_repair_context",
                ".lgwf/e2e_runtime_fake_observe.json",
            ),
            (
                "05_real_positive_e2e",
                "prepare_real_positive_observe_feedback",
                ".lgwf/e2e_real_positive_observe.json",
            ),
        )
        for workflow_dir, prepare_node, observe_path in contracts:
            with self.subTest(workflow_dir=workflow_dir):
                workflow = (ROOT / workflow_dir / "workflow.lgwf").read_text(encoding="utf-8")
                reason = (ROOT / workflow_dir / "01_design" / "agents" / "reason.md").read_text(encoding="utf-8")
                self.assertIn(prepare_node, workflow)
                self.assertIn(f'CONTEXT workspace file "{observe_path}"', workflow)
                self.assertIn(observe_path, reason)
                self.assertIn("initial_placeholder", reason)

    def test_runtime_fake_decide_writes_repair_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            write_json(
                work / ".lgwf" / "e2e_runtime_fake_observe.json",
                {
                    "passed": False,
                    "issues": ["fake 未命中真实 codex 命令"],
                    "contract_checks": {
                        "prompt_file_supported": {
                            "passed": False,
                            "issue_code": "fake_codex_command_not_intercepted",
                            "evidence": "command.json 显示 cmd.exe /c codex ... -",
                            "source_location": "command.json",
                            "repair_hint": "拦截 cmd.exe /c codex ... - 并从 stdin handoff 解析 Main prompt file。",
                        }
                    },
                    "scenario_checks": {},
                    "coverage_gaps": [],
                },
            )

            output = call_main("04_runtime_fake_e2e/04_repair/scripts/decide_runtime_fake.py", work, "decide_runtime_fake_once")

            result = json.loads(output)
            self.assertEqual(result["next"], "continue")
            context = read_json(work / ".lgwf" / "e2e_runtime_fake_repair_context.json")
            self.assertTrue(context["active"])
            self.assertFalse(context["no_progress"])
            self.assertEqual(context["blockers"][0]["issue_code"], "fake_codex_command_not_intercepted")
            self.assertEqual(result["lgwf_e2e.runtime_fake_repair_context"]["issue_signature"], context["issue_signature"])

    def test_runtime_fake_decide_stops_repeated_issue_signature(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            observe = {
                "passed": False,
                "issues": ["fake 未命中真实 codex 命令"],
                "contract_checks": {
                    "prompt_file_supported": {
                        "passed": False,
                        "issue_code": "fake_codex_command_not_intercepted",
                        "evidence": "command.json 显示 cmd.exe /c codex ... -",
                        "source_location": "command.json",
                        "repair_hint": "拦截 cmd.exe /c codex ... - 并从 stdin handoff 解析 Main prompt file。",
                    }
                },
                "scenario_checks": {},
                "coverage_gaps": [],
            }
            write_json(work / ".lgwf" / "e2e_runtime_fake_observe.json", observe)
            call_main("04_runtime_fake_e2e/04_repair/scripts/decide_runtime_fake.py", work, "decide_runtime_fake_first")

            output = call_main("04_runtime_fake_e2e/04_repair/scripts/decide_runtime_fake.py", work, "decide_runtime_fake_second")

            result = json.loads(output)
            self.assertEqual(result["next"], "exit")
            self.assertTrue(result["lgwf_e2e.runtime_fake_validation"]["no_progress"])
            context = read_json(work / ".lgwf" / "e2e_runtime_fake_repair_context.json")
            self.assertTrue(context["no_progress"])

    def test_finish_report_records_fixed_three_generated_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            request = {
                "workflow_lgwf": "D:/target/workflow.lgwf",
                "test_output_dir": "tests",
                "generated_tests": {
                    "script_flow": "test_sample_script_flow_e2e.py",
                    "runtime_fake": "test_sample_runtime_fake_e2e.py",
                    "real_positive": "test_sample_real_positive_e2e.py",
                },
            }
            write_json(work / ".lgwf" / "e2e_target_request.normalized.json", request)
            write_json(work / ".lgwf" / "e2e_coverage_matrix.json", {"script_flow": {"script_contracts": [], "routes": []}, "runtime_fake": {"output_json": []}})
            write_json(work / ".lgwf" / "e2e_script_flow_observe.json", {"passed": True})
            write_json(work / ".lgwf" / "e2e_runtime_fake_observe.json", {"passed": True})
            write_json(work / ".lgwf" / "e2e_real_positive_observe.json", {"passed": True})

            call_main("06_finish/01_generate_final_report/scripts/generate_final_report.py", work, "finish_report")

            report = read_json(work / "reports" / "e2e-test-generator" / "report.json")
            self.assertEqual(set(report["generated_tests"]), {"script_flow", "runtime_fake", "real_positive"})
            report_md = (work / "reports" / "e2e-test-generator" / "report.md").read_text(encoding="utf-8")
            self.assertIn("人工直接执行", report_md)


if __name__ == "__main__":
    unittest.main()
