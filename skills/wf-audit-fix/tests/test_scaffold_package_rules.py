from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ScaffoldRulesTest(unittest.TestCase):
    def test_root_files_exist(self) -> None:
        self.assertTrue((ROOT / "SKILL.md").is_file())
        self.assertTrue((ROOT / "AGENTS.md").is_file())
        self.assertTrue((ROOT / "README.md").is_file())

    def test_root_has_no_workflow_lgwf(self) -> None:
        self.assertFalse((ROOT / "workflow.lgwf").exists())
        self.assertTrue((ROOT / "wf" / "workflow.lgwf").is_file())

    def test_first_level_stage_workflows_exist(self) -> None:
        for rel in [
            "wf/02_confirm_requirements/workflow.lgwf",
            "wf/04_confirm_business_flow/workflow.lgwf",
            "wf/07_confirm_step_designs/workflow.lgwf",
            "wf/09_summarize_create_result/workflow.lgwf",
        ]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_stage_dirs_are_self_contained(self) -> None:
        for stage in [
            "02_confirm_requirements",
            "04_confirm_business_flow",
            "07_confirm_step_designs",
            "09_summarize_create_result",
        ]:
            base = ROOT / "wf" / stage
            self.assertTrue((base / "agents").exists(), stage)
            self.assertTrue((base / "scripts").exists(), stage)
            self.assertTrue((base / "resources").exists(), stage)


if __name__ == "__main__":
    unittest.main()
