from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = PACKAGE_ROOT.parents[1]
LGWF = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"

STAGES = [
    "01_collect_targets",
    "02_batch_audit",
    "03_classify_findings",
    "04_build_upgrade_plan",
    "05_confirm_upgrade_plan",
    "06_apply_upgrade_rules",
    "07_batch_verify",
    "08_summarize_upgrade_result",
]


class WorkflowDraftContractTests(unittest.TestCase):
    def compile_workflow(self, workflow_lgwf: Path) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "workflow.json"
            completed = subprocess.run(
                [sys.executable, str(LGWF), "compile", str(workflow_lgwf), "--output", str(output)],
                text=True,
                capture_output=True,
                cwd=FACADE_ROOT.parents[1],
            )
            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            return json.loads(output.read_text(encoding="utf-8"))

    def test_root_package_contract_files_exist(self) -> None:
        self.assertTrue((PACKAGE_ROOT / "AGENTS.md").is_file())
        self.assertTrue((PACKAGE_ROOT / "README.md").is_file())
        self.assertFalse((PACKAGE_ROOT / "SKILL.md").exists())
        self.assertTrue((PACKAGE_ROOT / "wf/workflow.lgwf").is_file())
        self.assertTrue((PACKAGE_ROOT / "wf/shared/scripts/upgrade_helpers.py").is_file())

    def test_root_workflow_only_sequences_eight_stage_workflows(self) -> None:
        text = (PACKAGE_ROOT / "wf/workflow.lgwf").read_text(encoding="utf-8")

        self.assertIn("ENTRY FLOW main", text)
        self.assertNotIn("RUN_WORKFLOW", text)
        for stage in STAGES:
            self.assertIn(f'WORKFLOW "{stage}/workflow.lgwf"', text)

        compiled = self.compile_workflow(PACKAGE_ROOT / "wf/workflow.lgwf")
        self.assertEqual("collect_targets_stage", compiled["entry_point"])
        self.assertEqual([], compiled["routes"])
        self.assertEqual(8, len(compiled["nodes"]))
        self.assertEqual(7, len(compiled["edges"]))

    def test_stage_directories_are_self_contained(self) -> None:
        for stage in STAGES:
            stage_dir = PACKAGE_ROOT / "wf" / stage
            self.assertTrue((stage_dir / "workflow.lgwf").is_file(), stage)
            self.assertTrue((stage_dir / "agents").is_dir(), stage)
            self.assertTrue((stage_dir / "scripts").is_dir(), stage)
            self.assertTrue((stage_dir / "resources").is_dir(), stage)

    def test_minimal_runtime_scripts_exist(self) -> None:
        expected = [
            "wf/01_collect_targets/scripts/build_target_manifest.py",
            "wf/02_batch_audit/scripts/run_batch_audit.py",
            "wf/03_classify_findings/scripts/classify_findings.py",
            "wf/04_build_upgrade_plan/scripts/build_upgrade_plan.py",
            "wf/05_confirm_upgrade_plan/scripts/prepare_upgrade_plan_approval.py",
            "wf/05_confirm_upgrade_plan/scripts/finalize_upgrade_plan_approval.py",
            "wf/06_apply_upgrade_rules/scripts/apply_upgrade_rules.py",
            "wf/07_batch_verify/scripts/verify_upgraded_workflows.py",
            "wf/08_summarize_upgrade_result/scripts/render_upgrade_summary.py",
        ]
        for relative in expected:
            self.assertTrue((PACKAGE_ROOT / relative).is_file(), relative)


if __name__ == "__main__":
    unittest.main()
