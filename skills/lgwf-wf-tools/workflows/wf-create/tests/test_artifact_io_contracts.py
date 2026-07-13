from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[4]
SOURCE_WF_ROOT = PACKAGE_ROOT / "wf"
TMP_ROOT = REPO_ROOT / ".tmp"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ArtifactIOContractsTest(unittest.TestCase):
    def setUp(self) -> None:
        TMP_ROOT.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(prefix="wf-create-artifacts-", dir=TMP_ROOT)
        self.work_dir = Path(self.temp_dir.name)
        self.workflow_root = self.work_dir / ".lgwf" / "workflow"
        shutil.copytree(SOURCE_WF_ROOT, self.workflow_root)
        (self.work_dir / ".lgwf").mkdir(exist_ok=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_script(self, relative_script: str, stdin_payload: dict | None = None) -> dict:
        input_text = "" if stdin_payload is None else json.dumps(stdin_payload, ensure_ascii=False)
        completed = subprocess.run(
            [sys.executable, str(self.workflow_root / relative_script)],
            cwd=self.work_dir,
            input=input_text,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_finish_raw_intent_reads_runtime_request_artifact(self) -> None:
        write_json(self.work_dir / ".lgwf" / "raw_intent_request.json", {"raw_intent": "创建 git-diff-brief"})

        result = self.run_script("01_confirm_requirements/01_raw_intent/scripts/finish_raw_intent.py")

        self.assertEqual(result["lgwf_wf_create.raw_intent_request"]["raw_intent"], "创建 git-diff-brief")

    def test_prepare_and_apply_raw_intent_confirmation_preserves_start_input(self) -> None:
        input_state = {
            "raw_intent": "创建 skill-packaging workflow",
            "request": {
                "target_file": "D:/allen/github/lgwf_wf_tools/docs_tmp/skill-packaging-wf-create-intent-design.md"
            },
        }

        prepared = self.run_script("01_confirm_requirements/01_raw_intent/scripts/prepare_confirmation.py", input_state)
        write_json(
            self.work_dir / ".lgwf" / "raw_intent_approval.json",
            {"decision": "approve", "approval": "approve", "comment": ""},
        )
        applied = self.run_script("01_confirm_requirements/01_raw_intent/scripts/apply_confirmed.py")
        finished = self.run_script("01_confirm_requirements/01_raw_intent/scripts/finish_raw_intent.py")

        proposal = prepared["lgwf_wf_create.raw_intent_confirmation_context"]["proposal"]
        self.assertEqual(proposal["raw_intent"], "创建 skill-packaging workflow")
        self.assertEqual(
            proposal["creation_context_files"],
            ["D:/allen/github/lgwf_wf_tools/docs_tmp/skill-packaging-wf-create-intent-design.md"],
        )
        self.assertEqual(applied["lgwf_wf_create.raw_intent_request"]["raw_intent"], "创建 skill-packaging workflow")
        self.assertEqual(finished["lgwf_wf_create.raw_intent_request"]["raw_intent"], "创建 skill-packaging workflow")

    def test_finish_raw_intent_exports_creation_context_targets(self) -> None:
        write_json(
            self.work_dir / ".lgwf" / "raw_intent_request.json",
            {
                "raw_intent": "创建 git-diff-brief",
                "creation_context_dirs": ["D:/plans/context"],
                "creation_context_files": ["D:/plans/workflow-plan.md"],
                "request": {
                    "target_dir": "D:/plans/context",
                    "target_dirs": ["D:/plans/extra-context"],
                    "target_file": "D:/plans/workflow-plan.md",
                    "target_files": ["D:/plans/notes.md"],
                },
            },
        )

        result = self.run_script("01_confirm_requirements/01_raw_intent/scripts/finish_raw_intent.py")

        self.assertEqual(
            result["lgwf_wf_create.creation_context_dirs"],
            ["D:/plans/context", "D:/plans/extra-context"],
        )
        self.assertEqual(
            result["lgwf_wf_create.creation_context_files"],
            ["D:/plans/workflow-plan.md", "D:/plans/notes.md"],
        )

    def test_prepare_confirmation_scripts_read_runtime_proposals(self) -> None:
        write_json(self.work_dir / ".lgwf" / "create_requirements_proposal.json", {"workflow_name": "git-diff-brief"})
        write_json(self.work_dir / ".lgwf" / "business_flow_proposal.json", {"stages": []})
        write_json(self.work_dir / ".lgwf" / "step_designs_proposal.json", {"step_designs": []})

        requirements = self.run_script("01_confirm_requirements/03_requirements_review/scripts/prepare_confirmation.py")
        business_flow = self.run_script("02_confirm_business_flow/scripts/prepare_business_flow_confirmation.py")
        step_designs = self.run_script("03_confirm_step_designs/scripts/prepare_step_design_confirmation.py")

        self.assertEqual(
            requirements["lgwf_wf_create.requirements_confirmation_context"]["approve_writes"],
            ".lgwf/create_requirements.json",
        )
        self.assertEqual(
            business_flow["lgwf_wf_create.business_flow_confirmation_context"]["approve_writes"],
            ".lgwf/business_flow.json",
        )
        self.assertEqual(
            step_designs["lgwf_wf_create.step_design_confirmation_context"]["approve_writes"],
            ".lgwf/step_designs.json",
        )

    def test_apply_confirmed_scripts_write_confirmed_runtime_artifacts(self) -> None:
        write_json(
            self.work_dir / ".lgwf" / "create_requirements_proposal.json",
            {
                "workflow_name": "git-diff-brief",
                "target_package_root": "skills/git-diff-brief",
            },
        )
        write_json(
            self.work_dir / ".lgwf" / "business_flow_proposal.json",
            {"workflow_name": "git-diff-brief", "stages": []},
        )
        write_json(
            self.work_dir / ".lgwf" / "step_designs_proposal.json",
            {"approved_step_slugs": ["collect-git-context"]},
        )
        write_json(
            self.work_dir / ".lgwf" / "create_requirements_approval.json",
            {"decision": "approve", "confirmed": {"approval": "approve"}},
        )
        write_json(
            self.work_dir / ".lgwf" / "business_flow_approval.json",
            {"decision": "approve", "confirmed": {"approval": "approve"}},
        )
        write_json(
            self.work_dir / ".lgwf" / "step_design_confirmation_record.json",
            {"decision": "approve", "confirmed": {"approval": "approve"}},
        )

        self.run_script("01_confirm_requirements/03_requirements_review/scripts/apply_confirmed.py")
        self.run_script("02_confirm_business_flow/scripts/apply_confirmed_business_flow.py")
        self.run_script("03_confirm_step_designs/scripts/apply_confirmed_step_designs.py")

        self.assertTrue((self.work_dir / ".lgwf" / "create_requirements.json").is_file())
        self.assertTrue((self.work_dir / ".lgwf" / "business_flow.json").is_file())
        self.assertTrue((self.work_dir / ".lgwf" / "step_designs.json").is_file())
        self.assertFalse((self.workflow_root / ".lgwf").exists())


if __name__ == "__main__":
    unittest.main()
