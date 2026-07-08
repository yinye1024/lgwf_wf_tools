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
sys.dont_write_bytecode = True


def run_script(work_dir: Path, relative: str) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(WF_ROOT / relative)],
        cwd=str(work_dir),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"{relative} failed\nSTDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}")
    return json.loads(completed.stdout or "{}")


class LgwfWfCreateRuntimeFakeE2ETest(unittest.TestCase):
    def assert_json_file(self, path: Path) -> dict:
        self.assertTrue(path.exists(), path.as_posix())
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.strip(), path.as_posix())
        self.assertNotIn("\ufeff", text[:1])
        payload = json.loads(text)
        self.assertIsInstance(payload, dict)
        return payload

    def write_json_file(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_workflow_route_matrix_covers_approve_and_reject_branches(self) -> None:
        workflow_text = (WF_ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("FLOW define_requirements", workflow_text)
        self.assertIn("THEN design_structure", workflow_text)
        self.assertIn("THEN implement_draft", workflow_text)
        self.assertIn("THEN summarize_create_result", workflow_text)
        self.assertNotIn('WHEN "approve" THEN design_structure', workflow_text)
        self.assertNotIn('WHEN "reject" THEN summarize_create_result', workflow_text)

        expected_routes = {
            "confirm_requirements": {
                "approve": "apply_confirmed_requirements",
                "revise": "confirm_requirements",
                "reject": "FAIL_ALL",
            },
            "confirm_business_flow": {
                "approve": "apply_confirmed_business_flow",
                "revise": "confirm_business_flow",
                "reject": "FAIL_ALL",
            },
            "confirm_step_designs": {
                "approve": "apply_confirmed_step_designs",
                "revise": "confirm_step_designs",
                "reject": "FAIL_ALL",
            },
        }
        child_workflow_text = "\n".join(
            (
                (WF_ROOT / "01_confirm_requirements/workflow.lgwf").read_text(encoding="utf-8"),
                (WF_ROOT / "02_confirm_business_flow/workflow.lgwf").read_text(encoding="utf-8"),
                (WF_ROOT / "03_confirm_step_designs/workflow.lgwf").read_text(encoding="utf-8"),
            )
        )
        for route_name, branches in expected_routes.items():
            self.assertIn("FLOW {", child_workflow_text)
            self.assertIn(route_name, child_workflow_text)
            for decision, target in branches.items():
                self.assertIn(f'WHEN "{decision}" THEN {target}', child_workflow_text)

        for node_name, persist_path in {
            "confirm_requirements": ".lgwf/create_requirements_approval.json",
            "confirm_business_flow": ".lgwf/business_flow_approval.json",
            "confirm_step_designs": ".lgwf/step_design_confirmation_record.json",
        }.items():
            node_start = child_workflow_text.index(f"REVIEW {node_name}")
            next_node = child_workflow_text.find("\n\n", node_start)
            node_block = child_workflow_text[node_start: next_node if next_node != -1 else len(child_workflow_text)]
            self.assertIn('OPTIONS ["approve", "revise", "reject"]', node_block)
            self.assertIn(f'PERSIST "{persist_path}"', node_block)

    def test_fake_runtime_approval_path_produces_expected_state_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            lgwf_dir = work_dir / ".lgwf"
            lgwf_dir.mkdir()

            fake_codex_outputs = {
                "create_requirements_proposal.json": {
                    "workflow_name": "fake_runtime_create",
                    "target_package_root": "skills/fake-runtime-create",
                    "requirements": [{"id": "r1", "description": "生成内部 workflow package"}],
                },
                "business_flow_proposal.json": {
                    "workflow_name": "fake_runtime_create",
                    "stages": [{"stage_id": "package_scaffold", "key_nodes": ["scaffold_package"]}],
                },
                "step_designs_proposal.json": {
                    "step_designs": [{"step_slug": "scaffold_package", "purpose": "生成 package 骨架"}],
                },
                "implementation_result.json": {
                    "status": "skipped_by_fake_runtime",
                    "notes": ["fake Codex path only verifies state handoff contracts"],
                },
            }
            for name, payload in fake_codex_outputs.items():
                (lgwf_dir / name).write_text(json.dumps(payload), encoding="utf-8")

            prepare_requirements = run_script(
                work_dir,
                "01_confirm_requirements/scripts/prepare_requirements_confirmation.py",
            )
            self.assertIn("lgwf_wf_create.requirements_confirmation_context", prepare_requirements)
            (lgwf_dir / "create_requirements_approval.json").write_text(
                json.dumps({"decision": "approve", "route": "approve", "comment": "确认通过"}),
                encoding="utf-8",
            )
            apply_requirements = run_script(
                work_dir,
                "01_confirm_requirements/scripts/apply_confirmed_requirements.py",
            )
            self.assertEqual(
                apply_requirements["lgwf_wf_create.apply_requirements_result"]["artifact_path"],
                ".lgwf/create_requirements.json",
            )

            prepare_business = run_script(
                work_dir,
                "02_confirm_business_flow/scripts/prepare_business_flow_confirmation.py",
            )
            self.assertIn("lgwf_wf_create.business_flow_confirmation_context", prepare_business)
            (lgwf_dir / "business_flow_approval.json").write_text(
                json.dumps({"decision": "approve", "route": "approve", "comment": "确认通过"}),
                encoding="utf-8",
            )
            run_script(work_dir, "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py")

            scaffold = run_script(work_dir, "02_confirm_business_flow/scripts/scaffold_package.py")
            scaffold_plan = scaffold["lgwf_wf_create.scaffold_package_result"]["scaffold_plan"]
            self.assertEqual(scaffold_plan["workflow_name"], "fake_runtime_create")
            self.assertIn("wf/workflow.lgwf", scaffold_plan["create_files"])

            prepare_steps = run_script(
                work_dir,
                "03_confirm_step_designs/scripts/prepare_step_design_confirmation.py",
            )
            self.assertIn("lgwf_wf_create.step_design_confirmation_context", prepare_steps)
            (lgwf_dir / "step_design_confirmation_record.json").write_text(
                json.dumps({"decision": "approve", "route": "approve", "comment": "确认通过"}),
                encoding="utf-8",
            )
            run_script(work_dir, "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py")

            summary_state = run_script(work_dir, "06_summarize_create_result/scripts/summarize_create_result.py")
            summary = json.loads((lgwf_dir / "create_result_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "draft_structure_ready")
            self.assertEqual(summary_state["status"], "draft_structure_ready")
            self.assertTrue((work_dir / "reports" / "create-workflow" / "create_result_report.md").exists())
            self.assertFalse(any(part in {".tmp", "__pycache__"} for path in os.listdir(work_dir) for part in Path(path).parts))

    def test_fake_runtime_branch_matrix_covers_files_format_read_and_write(self) -> None:
        stages = [
            {
                "name": "requirements",
                "proposal_file": "create_requirements_proposal.json",
                "proposal_payload": {
                    "workflow_name": "fake_branch_matrix",
                    "target_package_root": "skills/fake-branch-matrix",
                    "requirements": [{"id": "r1", "description": "生成 workflow package"}],
                },
                "prepare_script": "01_confirm_requirements/scripts/prepare_requirements_confirmation.py",
                "prepare_state_key": "lgwf_wf_create.requirements_confirmation_context",
                "approval_file": "create_requirements_approval.json",
                "revision_prepare_script": "01_confirm_requirements/scripts/prepare_requirements_revision_confirmation.py",
                "revision_state_key": "lgwf_wf_create.requirements_revision_context",
                "revision_approval_file": "create_requirements_revision_approval.json",
                "apply_script": "01_confirm_requirements/scripts/apply_confirmed_requirements.py",
                "apply_state_key": "lgwf_wf_create.apply_requirements_result",
                "output_file": "create_requirements.json",
                "artifact_kind": "create_requirements",
                "confirmed_payload": {
                    "workflow_name": "fake_branch_matrix",
                    "target_package_root": "skills/fake-branch-matrix",
                },
                "revised_confirmed_payload": {
                    "workflow_name": "fake_branch_matrix_revised",
                    "target_package_root": "skills/fake-branch-matrix",
                },
            },
            {
                "name": "business_flow",
                "proposal_file": "business_flow_proposal.json",
                "proposal_payload": {
                    "workflow_name": "fake_branch_matrix",
                    "stages": [{"stage_id": "scaffold_package", "key_nodes": ["scaffold_package"]}],
                },
                "prepare_script": "02_confirm_business_flow/scripts/prepare_business_flow_confirmation.py",
                "prepare_state_key": "lgwf_wf_create.business_flow_confirmation_context",
                "approval_file": "business_flow_approval.json",
                "revision_prepare_script": "02_confirm_business_flow/scripts/prepare_business_flow_revision_confirmation.py",
                "revision_state_key": "lgwf_wf_create.business_flow_revision_context",
                "revision_approval_file": "business_flow_revision_approval.json",
                "apply_script": "02_confirm_business_flow/scripts/apply_confirmed_business_flow.py",
                "apply_state_key": "lgwf_wf_create.apply_business_flow_result",
                "output_file": "business_flow.json",
                "artifact_kind": "business_flow",
                "confirmed_payload": {"stages": [{"stage_id": "scaffold_package"}]},
                "revised_confirmed_payload": {"stages": [{"stage_id": "scaffold_package"}, {"stage_id": "design_steps"}]},
            },
            {
                "name": "step_designs",
                "proposal_file": "step_designs_proposal.json",
                "proposal_payload": {
                    "step_designs": [{"step_slug": "scaffold_package", "purpose": "生成 package 骨架"}],
                },
                "prepare_script": "03_confirm_step_designs/scripts/prepare_step_design_confirmation.py",
                "prepare_state_key": "lgwf_wf_create.step_design_confirmation_context",
                "approval_file": "step_design_confirmation_record.json",
                "revision_prepare_script": "03_confirm_step_designs/scripts/prepare_step_design_revision_confirmation.py",
                "revision_state_key": "lgwf_wf_create.step_design_revision_context",
                "revision_approval_file": "step_design_revision_approval.json",
                "apply_script": "03_confirm_step_designs/scripts/apply_confirmed_step_designs.py",
                "apply_state_key": "lgwf_wf_create.apply_step_designs_result",
                "output_file": "step_designs.json",
                "artifact_kind": "step_designs",
                "confirmed_payload": {"step_designs": [{"step_slug": "scaffold_package"}]},
                "revised_confirmed_payload": {"step_designs": [{"step_slug": "scaffold_package"}, {"step_slug": "write_tests"}]},
            },
        ]

        for stage in stages:
            with self.subTest(stage=stage["name"], branch="approve"):
                with tempfile.TemporaryDirectory() as temp:
                    work_dir = Path(temp)
                    lgwf_dir = work_dir / ".lgwf"
                    self.write_json_file(lgwf_dir / stage["proposal_file"], stage["proposal_payload"])

                    prepare_state = run_script(work_dir, stage["prepare_script"])
                    self.assertIn(stage["prepare_state_key"], prepare_state)
                    self.assertEqual(
                        prepare_state[stage["prepare_state_key"]]["proposal"],
                        stage["proposal_payload"],
                    )

                    self.write_json_file(
                        lgwf_dir / stage["approval_file"],
                        {"decision": "approve", "route": "approve", "comment": "确认通过"},
                    )
                    apply_state = run_script(work_dir, stage["apply_script"])
                    result = apply_state[stage["apply_state_key"]]
                    artifact = self.assert_json_file(lgwf_dir / stage["output_file"])
                    self.assertEqual(artifact, result)
                    self.assertEqual(artifact["artifact_kind"], stage["artifact_kind"])
                    self.assertEqual(artifact["artifact_path"], f".lgwf/{stage['output_file']}")
                    self.assertEqual(artifact["source_approval_file"], f".lgwf/{stage['approval_file']}")
                    self.assertEqual(artifact["source_proposal_file"], f".lgwf/{stage['proposal_file']}")
                    self.assertEqual(artifact["decision"], "approve")
                    self.assertEqual(artifact["confirmed"], stage["proposal_payload"])
                    self.assertNotIn("approval", artifact)
                    for control_key in ("approval", "decision", "route", "changes", "comment", "request_id"):
                        self.assertNotIn(control_key, artifact["confirmed"])

            for decision in ("reject",):
                with self.subTest(stage=stage["name"], branch=f"{decision}_does_not_write_confirmed_artifact"):
                    with tempfile.TemporaryDirectory() as temp:
                        work_dir = Path(temp)
                        lgwf_dir = work_dir / ".lgwf"
                        self.write_json_file(
                            lgwf_dir / stage["approval_file"],
                            {"decision": decision, "confirmed": stage["confirmed_payload"]},
                        )

                        env = os.environ.copy()
                        env["PYTHONIOENCODING"] = "utf-8"
                        env["PYTHONDONTWRITEBYTECODE"] = "1"
                        completed = subprocess.run(
                            [sys.executable, str(WF_ROOT / stage["apply_script"])],
                            cwd=str(work_dir),
                            env=env,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False,
                        )
                        self.assertNotEqual(completed.returncode, 0)
                        self.assertIn("只有 approval=approve", completed.stderr)
                        self.assertFalse((lgwf_dir / stage["output_file"]).exists())


if __name__ == "__main__":
    unittest.main()
