from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WF_ROOT = PACKAGE_ROOT / "wf"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_script(work_dir: Path, relative: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(WF_ROOT / relative)],
        cwd=work_dir,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class ProposalQualityGateTest(unittest.TestCase):
    def test_business_flow_gate_passes_matching_current_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "business_flow_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "stages": [],
                },
            )

            completed = run_script(work_dir, "02_confirm_business_flow/scripts/validate_business_flow_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            result = payload["lgwf_wf_create.business_flow_proposal_quality_gate"]
            self.assertTrue(result["passed"])
            self.assertTrue((lgwf_dir / "business_flow_proposal_quality_gate.json").is_file())

    def test_requirements_gate_rejects_missing_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(lgwf_dir / "raw_intent_request.json", {"workflow_name": "demo"})

            completed = run_script(work_dir, "01_confirm_requirements/scripts/validate_requirements_proposal.py")

            self.assertNotEqual(completed.returncode, 0)
            result = json.loads((lgwf_dir / "create_requirements_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            self.assertIn("proposal_exists", [check["name"] for check in result["checks"] if not check["passed"]])

    def test_business_flow_gate_rejects_target_package_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "business_flow_proposal.json",
                {
                    "workflow_name": "demo",
                    "target_package_root": "skills/old-demo",
                    "stages": [],
                },
            )

            completed = run_script(work_dir, "02_confirm_business_flow/scripts/validate_business_flow_proposal.py")

            self.assertNotEqual(completed.returncode, 0)
            result = json.loads((lgwf_dir / "business_flow_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("target_package_root_matches", failures)
            self.assertIn("skills/old-demo", failures["target_package_root_matches"])

    def test_step_design_gate_rejects_stale_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "step_designs": [],
                },
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {"scaffold_plan": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            os.utime(lgwf_dir / "step_designs_proposal.json", (1000, 1000))
            os.utime(lgwf_dir / "scaffold_package_result.json", (2000, 2000))

            completed = run_script(work_dir, "03_confirm_step_designs/scripts/validate_step_designs_proposal.py")

            self.assertNotEqual(completed.returncode, 0)
            result = json.loads((lgwf_dir / "step_designs_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            self.assertIn("proposal_fresh_enough", [check["name"] for check in result["checks"] if not check["passed"]])


if __name__ == "__main__":
    unittest.main()
