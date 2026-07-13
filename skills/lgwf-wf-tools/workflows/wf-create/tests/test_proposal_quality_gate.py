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

            completed = run_script(work_dir, "02_confirm_business_flow/01_business_flow_proposal/scripts/validate_proposal.py")

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

            completed = run_script(work_dir, "01_confirm_requirements/02_requirements_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "create_requirements_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            self.assertIn("proposal_exists", [check["name"] for check in result["checks"] if not check["passed"]])

    def test_requirements_gate_treats_target_package_hint_as_reference_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(lgwf_dir / "raw_intent_request.json", {"target_package_hint": "demo workflow"})
            write_json(
                lgwf_dir / "create_requirements_proposal.json",
                {
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "requirements": [],
                },
            )

            completed = run_script(work_dir, "01_confirm_requirements/02_requirements_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "create_requirements_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertTrue(result["passed"])
            self.assertEqual(result["expected_identity"]["target_package_root"], "")
            self.assertEqual(result["reference_hints"]["target_package_hint"], "demo workflow")

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

            completed = run_script(work_dir, "02_confirm_business_flow/01_business_flow_proposal/scripts/validate_proposal.py")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "business_flow_proposal_quality_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("target_package_root_matches", failures)
            self.assertIn("skills/old-demo", failures["target_package_root_matches"])

    def test_business_flow_assert_quality_gate_rejects_failed_react_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow_proposal_quality_gate.json",
                {
                    "passed": False,
                    "checks": [
                        {
                            "name": "target_package_root_matches",
                            "passed": False,
                            "message": "target_package_root 不一致",
                        }
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "02_confirm_business_flow/01_business_flow_proposal/scripts/assert_quality_gate.py",
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("business flow proposal quality gate failed", completed.stderr)

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

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            self.assertIn("proposal_fresh_enough", [check["name"] for check in result["checks"] if not check["passed"]])

    def test_step_design_gate_rejects_doc_path_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stages": [{"stage_id": "prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {
                    "scaffold_plan": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stage_manifest": [{"stage_id": "prepare", "stage_dir": "01_prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "step_designs": [
                        {
                            "step_slug": "prepare",
                            "step_name": "准备",
                            "stage_id": "prepare",
                            "goal": "准备目标 workflow。",
                            "inputs": ["需求"],
                            "outputs": ["wf/01_prepare/workflow.lgwf"],
                            "dependencies": ["需求确认"],
                            "implementation_suggestions": ["生成阶段 workflow。"],
                            "acceptance_notes": ["阶段 workflow 存在。"],
                            "out_of_scope": ["端到端运行保证"],
                            "confirmation_points": ["阶段边界"],
                            "doc_path": "docs/steps/prepare.md",
                        }
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("step_designs[0]_doc_path_not_used", failures)

    def test_step_design_structural_gate_requires_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "business_flow.json",
                {
                    "confirmed": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stages": [{"stage_id": "prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "create_requirements.json",
                {"confirmed": {"workflow_name": "demo", "target_package_root": "skills/demo"}},
            )
            write_json(
                lgwf_dir / "scaffold_package_result.json",
                {
                    "scaffold_plan": {
                        "workflow_name": "demo",
                        "target_package_root": "skills/demo",
                        "stage_manifest": [{"stage_id": "prepare", "stage_dir": "01_prepare"}],
                    }
                },
            )
            write_json(
                lgwf_dir / "step_designs_proposal.json",
                {
                    "workflow_id": "demo",
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "step_designs": [
                        {
                            "step_slug": "prepare",
                            "step_name": "准备",
                            "stage_id": "prepare",
                            "goal": "准备目标 workflow。",
                            "inputs": ["需求"],
                            "outputs": ["wf/01_prepare/workflow.lgwf"],
                            "dependencies": ["需求确认"],
                            "implementation_suggestions": ["生成阶段 workflow。"],
                            "acceptance_notes": ["阶段 workflow 存在。"],
                            "out_of_scope": ["端到端运行保证"],
                            "confirmation_points": ["阶段边界"],
                        }
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/scripts/validate_step_designs_structure.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads((lgwf_dir / "step_design_structural_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(result["passed"])
            failures = {check["name"]: check["message"] for check in result["checks"] if not check["passed"]}
            self.assertIn("step_designs[0]_source_refs_present", failures)

    def test_step_design_observation_merge_blocks_on_structural_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "step_design_structural_gate.json",
                {
                    "passed": False,
                    "checks": [
                        {
                            "name": "step_designs[0]_source_refs_present",
                            "passed": False,
                            "message": "step_designs[0].source_refs 必须是非空数组",
                        }
                    ],
                },
            )
            write_json(
                lgwf_dir / "step_design_semantic_observation.json",
                {
                    "verdict": "pass",
                    "semantic_passed": True,
                    "blocking_issues": [],
                    "valid_parts_to_preserve": ["step_designs[0]"],
                    "reason_feedback": {
                        "repair_mode": "targeted_repair",
                        "priority_issue_ids": [],
                        "must_preserve": ["step_designs[0]"],
                        "must_change": [],
                        "forbidden_changes": ["不得写入 .lgwf/step_designs.json"],
                        "act_instruction_patch": [],
                    },
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/03_observe_step_designs/scripts/merge_step_design_observation.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            observation = json.loads((lgwf_dir / "step_design_observation.json").read_text(encoding="utf-8"))
            self.assertFalse(observation["passed"])
            self.assertEqual(observation["verdict"], "revise")
            self.assertIn("step_designs[0]_source_refs_present", observation["issue_signatures"])
            self.assertIn(
                "step_designs[0].source_refs 必须是非空数组",
                json.dumps(observation["reason_feedback"], ensure_ascii=False),
            )

    def test_step_design_decide_writes_continue_until_observation_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "step_design_observation.json",
                {
                    "passed": False,
                    "verdict": "revise",
                    "issue_signatures": ["stage_coverage.missing_prepare"],
                    "reason_feedback": {"repair_mode": "targeted_repair"},
                },
            )
            write_json(
                lgwf_dir / "step_design_decision_analysis.json",
                {
                    "recommended_next": "continue",
                    "reason": "仍有 blocker，需要下一轮 targeted repair。",
                    "no_progress_risk": False,
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/04_decide_step_designs/scripts/decide_step_designs.py",
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            decision = json.loads((lgwf_dir / "step_designs_proposal_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["next"], "continue")
            self.assertEqual(decision["next"], "continue")
            self.assertFalse(decision["passed"])

    def test_step_design_assert_quality_gate_rejects_failed_react_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            write_json(
                lgwf_dir / "step_designs_proposal_quality_gate.json",
                {
                    "passed": False,
                    "checks": [
                        {
                            "name": "proposal_fresh_enough",
                            "passed": False,
                            "message": "proposal 早于当前上游输入",
                        }
                    ],
                },
            )

            completed = run_script(
                work_dir,
                "03_confirm_step_designs/02_step_design_proposal/scripts/assert_quality_gate.py",
            )

            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("step designs proposal quality gate failed", completed.stderr)


if __name__ == "__main__":
    unittest.main()
