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
            self.assertEqual(normalized["real_codex_env"], "LGWF_SAMPLE_TARGET_REAL_CODEX_E2E")

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

    def test_finish_report_records_fixed_three_generated_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            request = {
                "workflow_lgwf": "D:/target/workflow.lgwf",
                "test_output_dir": "tests",
                "real_codex_env": "LGWF_SAMPLE_REAL_CODEX_E2E",
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
            self.assertTrue((work / "reports" / "e2e-test-generator" / "report.md").exists())


if __name__ == "__main__":
    unittest.main()
