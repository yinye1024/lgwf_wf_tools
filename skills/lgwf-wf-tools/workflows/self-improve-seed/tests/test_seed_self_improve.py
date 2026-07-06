from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "self-improve-seed" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import seed_self_improve  # noqa: E402


class SeedSelfImproveTest(unittest.TestCase):
    def test_install_creates_self_contained_self_improve_structure(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            target = create_demo_workflow(Path(raw_dir))

            result = seed_self_improve.seed_self_improve(target)

            self.assertEqual(target.resolve(), result["target_root"])
            manifest = json.loads((target / "self-improve" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("demo-workflow-self-improve", manifest["name"])
            self.assertEqual(2, manifest["version"])
            self.assertEqual(".local/self-improve", manifest["local_state_root"])
            self.assertIn("trace-eval", manifest["commands"])
            self.assertIn("check", manifest["commands"])
            self.assertTrue((target / "self-improve" / "scripts" / "self_improve.py").is_file())
            self.assertTrue((target / "self-improve" / "scripts" / "run_trace_eval.py").is_file())
            self.assertTrue((target / "self-improve" / "scripts" / "check_self_improve.py").is_file())
            self.assertTrue((target / "self-improve" / "evals" / "baseline-cases.json").is_file())
            self.assertTrue((target / "self-improve" / "templates" / "proposal.template.md").is_file())
            self.assertTrue((target / "self-improve" / "trace-eval" / "workflow.json").is_file())
            self.assertTrue(
                (
                    target
                    / "self-improve"
                    / "trace-eval"
                    / "golden_cases"
                    / "runtime_trace_contract"
                    / "spec.json"
                ).is_file()
            )

            for script in (target / "self-improve" / "scripts").glob("*.py"):
                text = script.read_text(encoding="utf-8")
                self.assertNotIn("lgwf-wf-tools", text)
                self.assertNotIn("workflows/self-improve", text)

    def test_generated_entrypoint_records_incident_and_proposal_without_wf_tools(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            target = create_demo_workflow(Path(raw_dir))

            seed_self_improve.seed_self_improve(target)
            entry = target / "self-improve" / "scripts" / "self_improve.py"
            incident = subprocess.run(
                [
                    sys.executable,
                    str(entry),
                    "incident",
                    "--type",
                    "routing",
                    "--summary",
                    "demo failure",
                    "--evidence-json",
                    "[]",
                ],
                cwd=target,
                text=True,
                capture_output=True,
                check=True,
            )
            incident_path = Path(json.loads(incident.stdout)["incident"])
            self.assertTrue(incident_path.is_file())

            proposal = subprocess.run(
                [sys.executable, str(entry), "proposal", "--incident", str(incident_path)],
                cwd=target,
                text=True,
                capture_output=True,
                check=True,
            )
            proposal_path = Path(json.loads(proposal.stdout)["proposal"])
            self.assertTrue(proposal_path.is_file())
            self.assertIn("Self Improve Proposal", proposal_path.read_text(encoding="utf-8"))
            self.assertIn("Trace Eval Evidence", proposal_path.read_text(encoding="utf-8"))

    def test_generated_trace_eval_and_check_run_against_target_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            target = create_demo_workflow(Path(raw_dir))
            seed_self_improve.seed_self_improve(target)
            entry = target / "self-improve" / "scripts" / "self_improve.py"

            self_eval = run_entry(target, entry, "eval")
            self.assertTrue(json.loads(self_eval.stdout)["passed"])

            trace_eval = run_entry(target, entry, "trace-eval")
            trace_payload = json.loads(trace_eval.stdout)
            self.assertTrue(trace_payload["passed"])
            trace_report = json.loads(Path(trace_payload["json"]).read_text(encoding="utf-8"))
            self.assertTrue(Path(trace_report["trace_path"]).is_file())
            self.assertTrue(Path(trace_report["eval_suite_path"]).is_file())
            self.assertEqual([], trace_report["failed_checks"])
            self.assertTrue((target / ".local" / "self-improve" / "reports" / "latest-trace-eval.json").is_file())

            check = run_entry(target, entry, "check")
            check_payload = json.loads(check.stdout)
            self.assertTrue(check_payload["passed"])
            self.assertTrue(Path(check_payload["json"]).is_file())
            self.assertTrue((target / ".local" / "self-improve" / "scorecards").is_dir())

    def test_generated_check_uses_timeout_for_each_step(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            target = create_demo_workflow(Path(raw_dir))
            seed_self_improve.seed_self_improve(target)

            script = (target / "self-improve" / "scripts" / "check_self_improve.py").read_text(encoding="utf-8")
            self.assertIn("DEFAULT_STEP_TIMEOUT_SECONDS", script)
            self.assertIn("timeout=timeout_seconds", script)
            self.assertIn("subprocess.TimeoutExpired", script)

    def test_scorecard_and_proposal_render_trace_eval_failures(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            target = create_demo_workflow(Path(raw_dir))
            seed_self_improve.seed_self_improve(target)
            report = target / ".local" / "self-improve" / "reports" / "latest-trace-eval.json"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(failed_trace_eval_report(), ensure_ascii=False), encoding="utf-8")
            entry = target / "self-improve" / "scripts" / "self_improve.py"

            scorecard = run_entry(target, entry, "scorecard")
            scorecard_path = Path(json.loads(scorecard.stdout)["scorecard"])
            scorecard_data = json.loads(scorecard_path.read_text(encoding="utf-8"))
            self.assertFalse(scorecard_data["trace_eval"]["passed"])
            self.assertEqual(3, scorecard_data["trace_eval"]["failed_check_count"])
            self.assertEqual(1, scorecard_data["trace_eval"]["destructive_policy_failure_count"])
            self.assertEqual(1, scorecard_data["trace_eval"]["forbidden_permission_failure_count"])
            self.assertEqual(1, scorecard_data["trace_eval"]["unexpected_route_failure_count"])

            incident = run_entry(
                target,
                entry,
                "incident",
                "--type",
                "runtime",
                "--summary",
                "trace eval failed",
                "--evidence-json",
                "[]",
            )
            incident_path = Path(json.loads(incident.stdout)["incident"])
            proposal = run_entry(target, entry, "proposal", "--incident", str(incident_path))
            proposal_text = Path(json.loads(proposal.stdout)["proposal"]).read_text(encoding="utf-8")
            self.assertIn("Trace Eval Evidence", proposal_text)
            self.assertIn("policy.forbidden_destructive", proposal_text)
            self.assertIn("exec.run_shell", proposal_text)
            self.assertIn("unexpected_route `True`", proposal_text)

    def test_install_refuses_to_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            target = create_demo_workflow(Path(raw_dir))
            (target / "self-improve").mkdir()

            with self.assertRaisesRegex(FileExistsError, "self-improve already exists"):
                seed_self_improve.seed_self_improve(target)

    def test_force_overwrites_with_v2_structure(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            target = create_demo_workflow(Path(raw_dir))
            (target / "self-improve").mkdir()
            (target / "self-improve" / "old.txt").write_text("old", encoding="utf-8")

            seed_self_improve.seed_self_improve(target, force=True)

            self.assertFalse((target / "self-improve" / "old.txt").exists())
            manifest = json.loads((target / "self-improve" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(2, manifest["version"])
            self.assertIn("trace-eval", manifest["commands"])


def create_demo_workflow(root: Path) -> Path:
    target = root / "demo-workflow"
    (target / "wf" / "scripts").mkdir(parents=True)
    (target / "AGENTS.md").write_text("# Demo Workflow\n", encoding="utf-8")
    (target / "wf" / "scripts" / "smoke.py").write_text(
        "from __future__ import annotations\n\nprint('{\"smoke\": {\"ok\": true}}')\n",
        encoding="utf-8",
    )
    (target / "wf" / "workflow.lgwf").write_text(
        """WORKFLOW demo;
ENTRY smoke;

DEFAULTS {
  ref_root workflow ".";
  timeout_seconds 30;
}

PY smoke
  SCRIPT "scripts/smoke.py"
  TIMEOUT 30
  RESULT state.smoke_result
  UPDATES_STATE;
""",
        encoding="utf-8",
    )
    return target


def run_entry(target: Path, entry: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(entry), *args],
        cwd=target,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=True,
    )


def failed_trace_eval_report() -> dict[str, object]:
    return {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "passed": False,
        "run_id": "run-001",
        "trace_path": ".lgwf/runs/run-001/trace.json",
        "eval_suite_path": ".lgwf/runs/run-001/eval-suite.json",
        "failed_cases": [{"case_id": "runtime_trace_contract", "description": "failed", "kind": "runtime_contract"}],
        "failed_checks": [
            {
                "case_id": "runtime_trace_contract",
                "check_name": "policy.forbidden_destructive",
                "message": "destructive capabilities used",
                "node_id": "run_shell",
                "capability": "exec.run_shell",
                "route": None,
                "client_call_id": None,
                "involves_destructive": True,
                "involves_forbidden_permission": False,
                "involves_unexpected_route": False,
            },
            {
                "case_id": "runtime_trace_contract",
                "check_name": "policy.forbidden_permissions",
                "message": "forbidden permissions used",
                "node_id": "run_shell",
                "capability": "exec.run_shell",
                "route": None,
                "client_call_id": None,
                "involves_destructive": False,
                "involves_forbidden_permission": True,
                "involves_unexpected_route": False,
            },
            {
                "case_id": "runtime_trace_contract",
                "check_name": "trajectory.forbidden_routes",
                "message": "forbidden route used",
                "node_id": "decide",
                "capability": None,
                "route": "fail",
                "client_call_id": "decide:check",
                "involves_destructive": False,
                "involves_forbidden_permission": False,
                "involves_unexpected_route": True,
            },
        ],
        "risk_summary": {
            "destructive_policy_failure_count": 1,
            "forbidden_permission_failure_count": 1,
            "unexpected_route_failure_count": 1,
        },
    }


if __name__ == "__main__":
    unittest.main()
