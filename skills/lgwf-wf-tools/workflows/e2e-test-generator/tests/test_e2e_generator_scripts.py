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
from unittest.mock import patch


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


def call_main(relative: str, cwd: Path, name: str, stdin_text: str | None = None) -> str:
    module = load_module(relative, name)
    output = StringIO()
    with pushd(cwd), redirect_stdout(output):
        if stdin_text is None:
            module.main()
        else:
            with patch("sys.stdin", StringIO(stdin_text)):
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
    def test_prepare_target_request_context_exports_business_request_for_auto_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            payload = {
                "workflow_lgwf": "skills/lgwf-wf-tools/workflows/skill-packaging/wf/workflow.lgwf",
                "workflow_root": "skills/lgwf-wf-tools/workflows/skill-packaging",
                "test_output_dir": "tests",
                "test_name_prefix": "skill_packaging",
                "test_types": ["script_flow", "runtime_fake"],
            }

            output = call_main(
                "01_inspect_target/00_collect_target_request/scripts/prepare_target_request_context.py",
                work,
                "prepare_target_request_with_input",
                json.dumps(payload, ensure_ascii=False),
            )

            state = json.loads(output)
            request = state["lgwf_e2e.target_request"]
            context = state["lgwf_e2e.target_request_context"]
            self.assertEqual(request["workflow_lgwf"], payload["workflow_lgwf"])
            self.assertEqual(request["workflow_root"], payload["workflow_root"])
            self.assertEqual(request["test_types"], ["script_flow", "runtime_fake"])
            self.assertEqual(context["candidate_request"]["workflow_lgwf"], payload["workflow_lgwf"])
            self.assertEqual(context["approval_target"], "e2e_target_request")

    def test_collect_target_request_approval_reads_business_request_not_context(self) -> None:
        workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        approval_block = workflow.split("APPROVAL collect_target_request", 1)[1].split("STEP inspect_target", 1)[0]
        self.assertIn("READ state.lgwf_e2e.target_request", approval_block)
        self.assertNotIn("READ state.lgwf_e2e.target_request_context", approval_block)

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
            self.assertEqual(normalized["generated_tests"]["real_positive"], "lgwf_sample_target_real_positive_e2e.py")
            self.assertEqual(
                normalized["generated_tests"]["wf_fix_positive"],
                "lgwf_sample_target_real_positive_e2e_for_wf_fix.py",
            )
            self.assertFalse(normalized["generated_tests"]["real_positive"].startswith("test_"))
            self.assertFalse(normalized["generated_tests"]["wf_fix_positive"].startswith("test_"))
            self.assertEqual(
                normalized["selected_test_types"],
                ["script_flow", "runtime_fake", "real_positive", "wf_fix_positive"],
            )
            self.assertNotIn("real_codex_env", normalized)

    def test_validate_target_request_resolves_facade_relative_path_in_run_workflow_isolation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            isolation = Path(temp) / "run_workflow" / "e2e_generate"
            work = isolation / "work_dir"
            workspace = isolation / "workspace"
            package_root = workspace / "workflows" / "skill-packaging"
            workflow_dir = package_root / "wf"
            work.mkdir(parents=True)
            workflow_dir.mkdir(parents=True)
            workflow = create_target_workflow(workflow_dir)
            write_json(
                work / ".lgwf" / "e2e_target_request.json",
                {
                    "workflow_lgwf": "skills/lgwf-wf-tools/workflows/skill-packaging/wf/workflow.lgwf",
                    "workflow_root": "skills/lgwf-wf-tools/workflows/skill-packaging",
                },
            )

            call_main("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", work, "validate_isolated")

            normalized = read_json(work / ".lgwf" / "e2e_target_request.normalized.json")
            self.assertEqual(Path(normalized["workflow_lgwf"]).resolve(), workflow.resolve())
            self.assertEqual(Path(normalized["workflow_root"]).resolve(), package_root.resolve())

    def test_validate_target_request_normalizes_selected_test_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            workflow = create_target_workflow(target)
            write_json(
                work / ".lgwf" / "e2e_target_request.json",
                {
                    "workflow_lgwf": workflow.as_posix(),
                    "test_types": ["wf_fix_positive", "runtime_fake", "runtime_fake"],
                },
            )

            call_main("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", work, "validate_selected")

            normalized = read_json(work / ".lgwf" / "e2e_target_request.normalized.json")
            self.assertEqual(normalized["selected_test_types"], ["runtime_fake", "wf_fix_positive"])

    def test_validate_target_request_rejects_unknown_test_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            workflow = create_target_workflow(target)
            write_json(
                work / ".lgwf" / "e2e_target_request.json",
                {"workflow_lgwf": workflow.as_posix(), "test_types": ["runtime_fake", "bad_kind"]},
            )

            with self.assertRaisesRegex(SystemExit, "invalid test_types"):
                call_main("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", work, "validate_bad_types")

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

    def test_summarize_business_flow_uses_deterministic_script(self) -> None:
        workflow_text = (ROOT / "01_inspect_target" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("PY summarize_business_flow", workflow_text)
        self.assertIn('SCRIPT "04_summarize_business_flow/scripts/summarize_business_flow.py"', workflow_text)
        self.assertNotIn("CODEX summarize_business_flow", workflow_text)

        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            workflow = create_target_workflow(target)
            write_json(work / ".lgwf" / "e2e_target_request.json", {"workflow_lgwf": workflow.as_posix()})

            for relative, name in (
                ("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", "validate_summary"),
                ("01_inspect_target/02_scan_workflow_package/scripts/scan_workflow_package.py", "scan_summary"),
                ("01_inspect_target/03_parse_workflow_graph/scripts/parse_workflow_graph.py", "parse_summary"),
                ("01_inspect_target/04_summarize_business_flow/scripts/summarize_business_flow.py", "summarize_flow"),
            ):
                call_main(relative, work, name)

            summary = read_json(work / ".lgwf" / "e2e_business_flow_summary.json")
            self.assertIn("sample_target", summary["summary"])
            self.assertTrue(summary["main_flow"])
            self.assertEqual(summary["approval_points"][0]["node_id"], "confirm")
            self.assertEqual(summary["route_points"][0]["route_id"], "choose_next")
            artifact_nodes = {item["node_id"] for item in summary["codex_artifacts"]}
            self.assertTrue({"generate_json", "repair_loop"}.issubset(artifact_nodes))
            self.assertEqual(
                set(summary["test_focus"]),
                {"script_flow", "runtime_fake", "real_positive", "wf_fix_positive"},
            )

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
            normalized = read_json(work / ".lgwf" / "e2e_target_request.normalized.json")
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
                "python tests/lgwf_sample_target_real_positive_e2e.py",
            )
            self.assertFalse(matrix["wf_fix_positive"]["discover_collected"])
            self.assertEqual(
                matrix["wf_fix_positive"]["manual_run_command"],
                "python tests/lgwf_sample_target_real_positive_e2e_for_wf_fix.py",
            )
            self.assertEqual(matrix["wf_fix_positive"]["target_workflow_lgwf"], normalized["workflow_lgwf"])
            self.assertEqual(matrix["wf_fix_positive"]["scenario_source"], ".lgwf/e2e_real_positive_design.json")
            self.assertTrue(matrix["script_flow"]["selected"])
            self.assertTrue(matrix["runtime_fake"]["selected"])
            self.assertTrue(matrix["real_positive"]["selected"])
            self.assertTrue(matrix["wf_fix_positive"]["selected"])
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

    def test_coverage_matrix_marks_only_selected_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            workflow = create_target_workflow(target)
            write_json(
                work / ".lgwf" / "e2e_target_request.json",
                {"workflow_lgwf": workflow.as_posix(), "test_types": ["runtime_fake", "wf_fix_positive"]},
            )

            for relative, name in (
                ("01_inspect_target/01_validate_target_request/scripts/validate_target_request.py", "validate_cov_selected"),
                ("01_inspect_target/02_scan_workflow_package/scripts/scan_workflow_package.py", "scan_cov_selected"),
                ("01_inspect_target/03_parse_workflow_graph/scripts/parse_workflow_graph.py", "parse_cov_selected"),
                ("02_derive_coverage_matrix/01_build_coverage_matrix/scripts/build_coverage_matrix.py", "coverage_selected"),
            ):
                call_main(relative, work, name)

            matrix = read_json(work / ".lgwf" / "e2e_coverage_matrix.json")
            self.assertFalse(matrix["script_flow"]["selected"])
            self.assertTrue(matrix["runtime_fake"]["selected"])
            self.assertFalse(matrix["real_positive"]["selected"])
            self.assertTrue(matrix["wf_fix_positive"]["selected"])

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
        self.assertIn('workspace file ".lgwf/e2e_runtime_fake_repair_context.json"', workflow)
        self.assertNotIn("REACT runtime_fake_e2e_react", workflow)
        self.assertNotIn("REASON CODEX", workflow)
        for node in (
            "design_runtime_fake_e2e",
            "generate_runtime_fake_e2e",
            "validate_runtime_fake_e2e",
        ):
            self.assertIn(node, workflow)

    def test_react_reason_prompts_receive_observe_feedback(self) -> None:
        contracts = (
            (
                "05_real_positive_e2e",
                "prepare_real_positive_observe_feedback",
                ".lgwf/e2e_real_positive_observe.json",
            ),
            (
                "06_wf_fix_positive_e2e",
                "prepare_wf_fix_positive_observe_feedback",
                ".lgwf/e2e_wf_fix_positive_observe.json",
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

    def test_script_flow_stage_uses_deterministic_scripts_not_codex_react(self) -> None:
        workflow = (ROOT / "03_script_flow_e2e" / "workflow.lgwf").read_text(encoding="utf-8")

        self.assertNotIn("REACT script_flow_e2e_react", workflow)
        self.assertNotIn("REASON CODEX", workflow)
        self.assertNotIn("ACT CODEX", workflow)
        self.assertNotIn("OBSERVE CODEX", workflow)
        for node in (
            "prepare_script_flow_observe_feedback",
            "design_script_flow_e2e",
            "generate_script_flow_e2e",
            "validate_script_flow_e2e",
        ):
            self.assertIn(node, workflow)

    def test_script_flow_scripts_generate_and_validate_without_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            (target / "scripts").mkdir()
            (target / "tests").mkdir()
            (target / "workflow.lgwf").write_text(
                """WORKFLOW target;
ENTRY prepare;

PY prepare
  SCRIPT "scripts/prepare.py"
  RESULT state.target.prepare;

APPROVAL confirm
  PROMPT "confirm"
  RESULT state.target.confirm
  PERSIST ".lgwf/confirm.json";

ROUTE choose_next
  WHEN "retry" THEN prepare
  WHEN "done" THEN finish;

PY finish
  SCRIPT "scripts/finish.py"
  RESULT state.target.finish;
""",
                encoding="utf-8",
            )
            (target / "scripts" / "prepare.py").write_text("def main():\n    return None\n", encoding="utf-8")
            (target / "scripts" / "finish.py").write_text("def main():\n    return None\n", encoding="utf-8")
            request = {
                "workflow_name": "target",
                "workflow_root": str(target),
                "workflow_lgwf": str(target / "workflow.lgwf"),
                "test_output_dir": "tests",
                "generated_tests": {"script_flow": "test_target_script_flow_e2e.py"},
                "selected_test_types": ["script_flow"],
            }
            matrix = {
                "script_flow": {
                    "selected": True,
                    "script_contracts": ["scripts/prepare.py", "scripts/finish.py"],
                    "routes": [
                        {"route_id": "choose_next", "value": "retry", "target": "prepare", "workflow": "workflow.lgwf"},
                        {"route_id": "choose_next", "value": "done", "target": "finish", "workflow": "workflow.lgwf"},
                    ],
                    "approval_persist": [".lgwf/confirm.json"],
                }
            }
            graph = {
                "workflow_name": "target",
                "workflows": [{"path": "workflow.lgwf"}],
                "scripts": matrix["script_flow"]["script_contracts"],
                "routes": [{"id": "choose_next", "workflow": "workflow.lgwf", "branches": matrix["script_flow"]["routes"]}],
                "persist": [".lgwf/confirm.json"],
            }
            write_json(work / ".lgwf" / "e2e_target_request.normalized.json", request)
            write_json(work / ".lgwf" / "e2e_coverage_matrix.json", matrix)
            write_json(work / ".lgwf" / "e2e_workflow_graph.json", graph)
            write_json(work / ".lgwf" / "e2e_script_flow_observe.json", {"initial_placeholder": True, "passed": False})

            call_main("03_script_flow_e2e/01_design/scripts/design_script_flow_e2e.py", work, "script_flow_design")
            design = read_json(work / ".lgwf" / "e2e_script_flow_design.json")
            self.assertEqual(design["test_file"], "tests/test_target_script_flow_e2e.py")
            self.assertGreaterEqual(len(design["cases"]), 3)
            self.assertTrue(any(case["case_id"] == "case_script_contracts_compile" for case in design["cases"]))
            self.assertTrue(any(claim["coverage_ref"] == "script_contracts" for claim in design["coverage_claims"]))

            call_main("03_script_flow_e2e/02_generate/scripts/generate_script_flow_e2e.py", work, "script_flow_generate")
            generated_test = target / "tests" / "test_target_script_flow_e2e.py"
            self.assertTrue(generated_test.exists())
            generation = read_json(work / ".lgwf" / "e2e_script_flow_generation.json")
            self.assertTrue(generation["generated"])
            self.assertTrue(generation["guard_mechanisms"])

            call_main("03_script_flow_e2e/03_validate/scripts/validate_script_flow_e2e.py", work, "script_flow_validate")
            observe = read_json(work / ".lgwf" / "e2e_script_flow_observe.json")
            self.assertTrue(observe["passed"], observe)
            self.assertTrue(observe["criterion_checks"]["py_compile"]["passed"])
            self.assertTrue(observe["criterion_checks"]["unittest"]["passed"])

    def test_runtime_fake_scripts_generate_and_validate_without_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp) / "work"
            target = Path(temp) / "target"
            work.mkdir()
            target.mkdir()
            (target / "tests").mkdir()
            (target / "workflow.lgwf").write_text(
                """WORKFLOW target;
ENTRY prepare;

CODEX generate
  PROMPT "agents/generate.md"
  OUTPUT_JSON ".lgwf/generated.json"
  RESULT state.target.generate;

APPROVAL confirm
  PROMPT "confirm"
  RESULT state.target.confirm
  PERSIST ".lgwf/confirm.json";

ROUTE choose_next
  WHEN "retry" THEN generate
  WHEN "done" THEN finish;

PY finish
  SCRIPT "scripts/finish.py"
  RESULT state.target.finish;
""",
                encoding="utf-8",
            )
            request = {
                "workflow_name": "target",
                "workflow_root": str(target),
                "workflow_lgwf": str(target / "workflow.lgwf"),
                "test_output_dir": "tests",
                "generated_tests": {"runtime_fake": "test_target_runtime_fake_e2e.py"},
                "selected_test_types": ["runtime_fake"],
            }
            matrix = {
                "runtime_fake": {
                    "selected": True,
                    "codex_like_nodes": [{"id": "generate", "kind": "CODEX", "workflow": "workflow.lgwf"}],
                    "approval_nodes": [{"id": "confirm", "kind": "APPROVAL", "workflow": "workflow.lgwf"}],
                    "routes": [
                        {"route_id": "choose_next", "value": "retry", "target": "generate", "workflow": "workflow.lgwf"},
                        {"route_id": "choose_next", "value": "done", "target": "finish", "workflow": "workflow.lgwf"},
                    ],
                    "output_json": [".lgwf/generated.json"],
                    "persist_artifacts": [".lgwf/confirm.json"],
                    "branch_targets": [
                        {"route_id": "choose_next", "value": "retry", "target": "generate", "workflow": "workflow.lgwf"},
                        {"route_id": "choose_next", "value": "done", "target": "finish", "workflow": "workflow.lgwf"},
                    ],
                    "repair_or_retry_nodes": [],
                }
            }
            graph = {
                "workflow_name": "target",
                "nodes": [
                    {"id": "generate", "kind": "CODEX", "workflow": "workflow.lgwf"},
                    {"id": "confirm", "kind": "APPROVAL", "workflow": "workflow.lgwf"},
                ],
                "routes": [{"id": "choose_next", "workflow": "workflow.lgwf", "branches": matrix["runtime_fake"]["routes"]}],
                "output_json": [".lgwf/generated.json"],
                "persist": [".lgwf/confirm.json"],
            }
            write_json(work / ".lgwf" / "e2e_target_request.normalized.json", request)
            write_json(work / ".lgwf" / "e2e_coverage_matrix.json", matrix)
            write_json(work / ".lgwf" / "e2e_workflow_graph.json", graph)
            write_json(work / ".lgwf" / "e2e_runtime_fake_observe.json", {"initial_placeholder": True, "passed": False})
            write_json(work / ".lgwf" / "e2e_runtime_fake_repair_context.json", {"active": False, "blockers": [], "history_count": 0})

            call_main("04_runtime_fake_e2e/01_design/scripts/design_runtime_fake_e2e.py", work, "runtime_fake_design")
            design = read_json(work / ".lgwf" / "e2e_runtime_fake_design.json")
            self.assertEqual(design["test_file"], "tests/test_target_runtime_fake_e2e.py")
            self.assertTrue(any(scenario["scenario_id"] == "happy_path" for scenario in design["scenarios"]))
            self.assertTrue(design["fake_codex_contract"]["prompt_file_support"])

            call_main("04_runtime_fake_e2e/02_generate/scripts/generate_runtime_fake_e2e.py", work, "runtime_fake_generate")
            generated_test = target / "tests" / "test_target_runtime_fake_e2e.py"
            self.assertTrue(generated_test.exists())
            source = generated_test.read_text(encoding="utf-8")
            self.assertIn("lgwf.py run --workflow-lgwf", source)
            self.assertIn("--prompt-file", source)
            self.assertIn("approval submit", source)

            call_main("04_runtime_fake_e2e/03_validate/scripts/validate_runtime_fake_e2e.py", work, "runtime_fake_validate")
            observe = read_json(work / ".lgwf" / "e2e_runtime_fake_observe.json")
            self.assertTrue(observe["passed"], observe)
            self.assertTrue(observe["contract_checks"]["business_route_coverage"]["passed"])

    def test_wf_fix_positive_prompts_define_driver_contract(self) -> None:
        workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        spec = (ROOT / "06_wf_fix_positive_e2e" / "01_design" / "agents" / "spec.md").read_text(encoding="utf-8")
        design = (ROOT / "06_wf_fix_positive_e2e" / "01_design" / "agents" / "reason.md").read_text(encoding="utf-8")
        generate = (ROOT / "06_wf_fix_positive_e2e" / "02_generate" / "agents" / "act.md").read_text(encoding="utf-8")
        observe = (ROOT / "06_wf_fix_positive_e2e" / "03_validate" / "agents" / "observe.md").read_text(encoding="utf-8")

        self.assertIn("STEP wf_fix_positive_e2e", workflow)
        self.assertIn('WORKFLOW "06_wf_fix_positive_e2e/workflow.lgwf"', workflow)
        self.assertIn("THEN wf_fix_positive_e2e", workflow)
        for node in (
            "route_script_flow_selection",
            "route_runtime_fake_selection",
            "route_real_positive_selection",
            "route_wf_fix_positive_selection",
        ):
            self.assertIn(node, workflow)
        self.assertIn('WHEN "run" THEN script_flow_e2e', workflow)
        self.assertIn('WHEN "skip" THEN route_runtime_fake_selection', workflow)
        for token in (
            "wf-fix",
            "target_workflow_lgwf",
            "ask_main_agent_for_target_approvals=true",
            "max_attempts=5",
            "e2e_real_positive_design.json",
        ):
            self.assertIn(token, spec)
            self.assertIn(token, design)
        for token in (
            "lgwf_<workflow>_real_positive_e2e_for_wf_fix.py",
            "skills/lgwf-wf-tools/workflows/wf-fix/wf/workflow.lgwf",
            "target_workflow_lgwf",
            "target_workflow_input",
            "自动处理 approval",
            "self_fix_summary",
            "artifact",
        ):
            self.assertIn(token, generate)
        for token in (
            "不真实启动 `wf-fix`",
            "discover_collected",
            "manual_filename_present",
            "wf_fix_summary_assertions_present",
            "artifact_retention_present",
        ):
            self.assertIn(token, observe)

    def test_real_positive_prompts_require_audit_check(self) -> None:
        spec = (ROOT / "05_real_positive_e2e" / "01_design" / "agents" / "spec.md").read_text(encoding="utf-8")
        design = (ROOT / "05_real_positive_e2e" / "01_design" / "agents" / "reason.md").read_text(encoding="utf-8")
        generate = (ROOT / "05_real_positive_e2e" / "02_generate" / "agents" / "act.md").read_text(encoding="utf-8")
        observe = (ROOT / "05_real_positive_e2e" / "03_validate" / "agents" / "observe.md").read_text(encoding="utf-8")

        for token in (
            "lgwf.py audit",
            "原始目标 `workflow.lgwf`",
            "audit 输出",
            "artifact",
        ):
            self.assertIn(token, spec)
        for token in (
            "audit_check",
            "command",
            "target",
            "failure_behavior",
            "retained_outputs",
        ):
            self.assertIn(token, design)
        for token in (
            "lgwf.py audit",
            "workflow.lgwf",
            "audit 失败",
            "保留",
            "audit 输出",
        ):
            self.assertIn(token, generate)
        for token in (
            "audit_check_present",
            "lgwf.py audit",
            "目标 workflow 路径",
            "audit 输出",
            "artifact",
        ):
            self.assertIn(token, observe)

    def test_wf_fix_positive_prompts_require_target_audit_check(self) -> None:
        spec = (ROOT / "06_wf_fix_positive_e2e" / "01_design" / "agents" / "spec.md").read_text(encoding="utf-8")
        design = (ROOT / "06_wf_fix_positive_e2e" / "01_design" / "agents" / "reason.md").read_text(encoding="utf-8")
        generate = (ROOT / "06_wf_fix_positive_e2e" / "02_generate" / "agents" / "act.md").read_text(encoding="utf-8")
        observe = (ROOT / "06_wf_fix_positive_e2e" / "03_validate" / "agents" / "observe.md").read_text(encoding="utf-8")

        for token in (
            "lgwf.py audit",
            "原始目标 `workflow.lgwf`",
            "不得 audit Python 脚本",
            "不得 audit `wf-fix` 自身",
            "audit 输出",
        ):
            self.assertIn(token, spec)
        for token in (
            "audit_check",
            "forbidden_targets",
            "生成的 Python 脚本",
            "wf-fix workflow.lgwf",
            "retained_outputs",
        ):
            self.assertIn(token, design)
        for token in (
            "lgwf.py audit",
            "原始目标 workflow",
            "不得 audit Python 脚本",
            "不得 audit `wf-fix` 自身",
            "audit 失败",
            "audit 输出",
        ):
            self.assertIn(token, generate)
        for token in (
            "audit_check_present",
            "原始目标 workflow",
            "不得 audit Python 脚本",
            "不得 audit `wf-fix` 自身",
            "audit 输出",
        ):
            self.assertIn(token, observe)

    def test_selection_route_scripts_emit_runtime_route_keys(self) -> None:
        workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        for node_id in (
            "route_script_flow_selection",
            "route_runtime_fake_selection",
            "route_real_positive_selection",
            "route_wf_fix_positive_selection",
        ):
            with self.subTest(contract=node_id):
                block = workflow.split(f"PY {node_id}", 1)[1].split("};", 1)[0]
                self.assertNotIn("WRITE workspace file", block)

        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            write_json(
                work / ".lgwf" / "e2e_target_request.normalized.json",
                {
                    "selected_test_types": ["wf_fix_positive"],
                    "generated_tests": {
                        "script_flow": "test_target_script_flow_e2e.py",
                        "runtime_fake": "test_target_runtime_fake_e2e.py",
                        "real_positive": "lgwf_target_real_positive_e2e.py",
                        "wf_fix_positive": "lgwf_target_real_positive_e2e_for_wf_fix.py",
                    },
                },
            )
            cases = [
                ("route_script_flow_selection", "script_flow", "skip"),
                ("route_runtime_fake_selection", "runtime_fake", "skip"),
                ("route_real_positive_selection", "real_positive", "skip"),
                ("route_wf_fix_positive_selection", "wf_fix_positive", "run"),
            ]
            artifact_names = {
                "script_flow": ("e2e_script_flow_generation.json", "e2e_script_flow_observe.json"),
                "runtime_fake": ("e2e_runtime_fake_generation.json", "e2e_runtime_fake_observe.json"),
                "real_positive": ("e2e_real_positive_generation.json", "e2e_real_positive_observe.json"),
                "wf_fix_positive": ("e2e_wf_fix_positive_generation.json", "e2e_wf_fix_positive_observe.json"),
            }

            for node_id, module_suffix, expected in cases:
                with self.subTest(node_id=node_id):
                    output = call_main(
                        f"00_route_selection/scripts/{node_id}.py",
                        work,
                        f"route_{module_suffix}_once",
                    )
                    result = json.loads(output)
                    self.assertEqual(result[f"__route__{node_id}"], expected)
                    self.assertEqual(result["next"], expected)
                    self.assertEqual(result["selected"], expected == "run")
                    generation_name, observe_name = artifact_names[module_suffix]
                    generation_path = work / ".lgwf" / generation_name
                    observe_path = work / ".lgwf" / observe_name
                    if expected == "skip":
                        self.assertEqual(read_json(generation_path)["status"], "skipped")
                        self.assertEqual(read_json(observe_path)["status"], "skipped")
                    else:
                        self.assertFalse(generation_path.exists())
                        self.assertFalse(observe_path.exists())

    def test_wf_fix_positive_prepare_creates_real_positive_design_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)

            call_main(
                "06_wf_fix_positive_e2e/00_prepare/scripts/prepare_wf_fix_positive_observe_feedback.py",
                work,
                "prepare_wf_fix_positive_once",
            )

            design = read_json(work / ".lgwf" / "e2e_real_positive_design.json")
            observe = read_json(work / ".lgwf" / "e2e_wf_fix_positive_observe.json")
            self.assertTrue(design["source_missing"])
            self.assertIn("等价固定正向场景", design["summary"])
            self.assertTrue(observe["initial_placeholder"])

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

    def test_finish_report_records_fixed_four_generated_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            request = {
                "workflow_lgwf": "D:/target/workflow.lgwf",
                "test_output_dir": "tests",
                "selected_test_types": ["runtime_fake", "wf_fix_positive"],
                "generated_tests": {
                    "script_flow": "test_sample_script_flow_e2e.py",
                    "runtime_fake": "test_sample_runtime_fake_e2e.py",
                    "real_positive": "lgwf_sample_real_positive_e2e.py",
                    "wf_fix_positive": "lgwf_sample_real_positive_e2e_for_wf_fix.py",
                },
            }
            write_json(work / ".lgwf" / "e2e_target_request.normalized.json", request)
            write_json(
                work / ".lgwf" / "e2e_coverage_matrix.json",
                {"script_flow": {"script_contracts": [], "routes": []}, "runtime_fake": {"output_json": []}},
            )
            write_json(work / ".lgwf" / "e2e_script_flow_observe.json", {"passed": True})
            write_json(work / ".lgwf" / "e2e_runtime_fake_observe.json", {"passed": True})
            write_json(work / ".lgwf" / "e2e_wf_fix_positive_observe.json", {"passed": True})

            call_main("07_finish/01_generate_final_report/scripts/generate_final_report.py", work, "finish_report")

            report = read_json(work / "reports" / "e2e-test-generator" / "report.json")
            self.assertEqual(set(report["generated_tests"]), {"script_flow", "runtime_fake", "real_positive", "wf_fix_positive"})
            self.assertEqual(report["selected_test_types"], ["runtime_fake", "wf_fix_positive"])
            self.assertEqual(report["validations"]["script_flow"]["status"], "skipped")
            self.assertEqual(report["validations"]["real_positive"]["status"], "skipped")
            self.assertTrue(report["validations"]["runtime_fake"]["passed"])
            self.assertTrue(report["validations"]["wf_fix_positive"]["passed"])
            report_md = (work / "reports" / "e2e-test-generator" / "report.md").read_text(encoding="utf-8")
            self.assertIn("人工直接执行", report_md)
            self.assertIn("wf-fix", report_md)
            self.assertIn("wf_fix_positive", report_md)
            self.assertIn("skipped", report_md)


if __name__ == "__main__":
    unittest.main()
