from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    return subprocess.run(
        [sys.executable, "-m", "lgwf_dsl.cli", *args],
        cwd=str(cwd or ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class RuntimeDebugAndExplainTest(unittest.TestCase):
    def test_audit_debug_runtime_reports_import_source_and_features(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "noop.py").write_text("print('{}')\n", encoding="utf-8")
            workflow = root / "workflow.lgwf"
            workflow.write_text(
                """
WORKFLOW demo;
ENTRY a;
PY a SCRIPT "noop.py";
PY b SCRIPT "noop.py";
FLOW a THEN b;
""",
                encoding="utf-8",
            )

            completed = run_cli(["audit", str(workflow), "--debug-runtime"])

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        payload = json.loads(completed.stdout)
        runtime = payload.get("runtime_debug")
        self.assertIsInstance(runtime, dict)
        self.assertTrue(str(runtime.get("lgwf_dsl_file", "")).endswith("__init__.py"))
        self.assertTrue(runtime.get("supports_flow_block"))
        self.assertTrue(runtime.get("artifact_contract_auditor_enabled"))

    def test_explain_projects_route_branches_as_route_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "noop.py").write_text("print('{}')\n", encoding="utf-8")
            workflow = root / "workflow.lgwf"
            workflow.write_text(
                """
WORKFLOW block_flow_demo;
ENTRY define_requirements;
PY define_requirements SCRIPT "noop.py";
PY design_structure SCRIPT "noop.py";
PY summarize_create_result SCRIPT "noop.py";
FLOW {
  define_requirements
    WHEN "approve" THEN design_structure
    WHEN "reject" THEN summarize_create_result;
}
""",
                encoding="utf-8",
            )

            completed = run_cli(["audit", str(workflow)])

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        explain = json.loads(completed.stdout)["explain"]
        self.assertEqual(explain["edges"], [])
        self.assertEqual(
            sorted(explain["route_edges"], key=lambda item: item["decision"]),
            [
                {"from": "define_requirements", "to": "design_structure", "decision": "approve"},
                {"from": "define_requirements", "to": "summarize_create_result", "decision": "reject"},
            ],
        )

    def test_explain_projects_nested_workflow_route_edges_with_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            child = root / "child"
            child.mkdir()
            (root / "noop.py").write_text("print('{}')\n", encoding="utf-8")
            (child / "noop.py").write_text("print('{}')\n", encoding="utf-8")
            (child / "workflow.lgwf").write_text(
                """
WORKFLOW child;
ENTRY a;
PY a SCRIPT "noop.py";
PY b SCRIPT "noop.py";
PY c SCRIPT "noop.py";
FLOW {
  a
    WHEN "approve" THEN b
    WHEN "reject" THEN c;
}
""",
                encoding="utf-8",
            )
            workflow = root / "workflow.lgwf"
            workflow.write_text(
                """
WORKFLOW parent;
ENTRY child_step;
STEP child_step WORKFLOW "child/workflow.lgwf";
PY finish SCRIPT "noop.py";
FLOW child_step THEN finish;
""",
                encoding="utf-8",
            )

            completed = run_cli(["audit", str(workflow)])

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        route_edges = json.loads(completed.stdout)["explain"]["route_edges"]
        self.assertIn(
            {"from": "child_step.a", "to": "child_step.b", "decision": "approve"},
            route_edges,
        )
        self.assertIn(
            {"from": "child_step.a", "to": "child_step.c", "decision": "reject"},
            route_edges,
        )


if __name__ == "__main__":
    unittest.main()
