from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
STAGES = [
    "01_prepare_packaging_request",
    "02_preflight_packaging_plan",
    "03_confirm_packaging_plan",
    "04_materialize_packaged_skill",
    "05_verify_packaged_skill",
    "06_summarize_packaging_result",
]
STEP_DOCS = [
    "prepare-packaging-request.md",
    "preflight-packaging-plan.md",
    "confirm-packaging-plan.md",
    "materialize-packaged-skill.md",
    "verify-packaged-skill.md",
    "summarize-packaging-result.md",
]


class ScaffoldRulesTest(unittest.TestCase):
    def test_root_files_match_internal_workflow_package(self) -> None:
        self.assertTrue((ROOT / "AGENTS.md").is_file())
        self.assertTrue((ROOT / "README.md").is_file())
        self.assertFalse((ROOT / "SKILL.md").exists())

    def test_root_has_only_wf_workflow_entry(self) -> None:
        self.assertFalse((ROOT / "workflow.lgwf").exists())
        self.assertTrue((ROOT / "wf" / "workflow.lgwf").is_file())

    def test_first_level_stage_workflows_exist(self) -> None:
        for stage in STAGES:
            self.assertTrue((ROOT / "wf" / stage / "workflow.lgwf").is_file(), stage)

    def test_stage_dirs_are_self_contained(self) -> None:
        for stage in STAGES:
            base = ROOT / "wf" / stage
            self.assertTrue((base / "agents").exists(), stage)
            self.assertTrue((base / "scripts").exists(), stage)
            self.assertTrue((base / "resources").exists(), stage)

    def test_no_grandchild_workflow_exists(self) -> None:
        for path in (ROOT / "wf").rglob("workflow.lgwf"):
            rel = path.relative_to(ROOT).as_posix()
            if rel == "wf/workflow.lgwf":
                continue
            self.assertLessEqual(len(Path(rel).parts), 3, rel)

    def test_step_design_docs_are_copied_into_target_package(self) -> None:
        docs_root = ROOT / "wf" / "docs" / "steps"
        self.assertTrue(docs_root.is_dir())
        for name in STEP_DOCS:
            self.assertTrue((docs_root / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
