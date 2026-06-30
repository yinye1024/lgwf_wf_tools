from __future__ import annotations

import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class PackageStructureTest(unittest.TestCase):
    def test_internal_workflow_package_has_expected_roots(self) -> None:
        self.assertTrue((PACKAGE_ROOT / "AGENTS.md").exists())
        self.assertTrue((PACKAGE_ROOT / "README.md").exists())
        self.assertTrue((PACKAGE_ROOT / "wf" / "workflow.lgwf").exists())
        self.assertTrue((PACKAGE_ROOT / "tests" / "README.md").exists())
        self.assertTrue((PACKAGE_ROOT / "wf" / "shared" / "scripts" / "confirmation_io.py").exists())
        self.assertFalse((PACKAGE_ROOT / "SKILL.md").exists())
        self.assertFalse((PACKAGE_ROOT / "workflow.lgwf").exists())

    def test_stage_workflows_are_first_layer_only(self) -> None:
        expected = [
            "01_request_scope_alignment",
            "02_git_context_collection",
            "03_brief_synthesis",
            "04_result_review_and_delivery",
        ]
        for stage in expected:
            stage_root = PACKAGE_ROOT / "wf" / stage
            self.assertTrue((stage_root / "workflow.lgwf").exists(), stage)
            self.assertTrue((stage_root / "agents").is_dir(), stage)
            self.assertTrue((stage_root / "scripts").is_dir(), stage)
            self.assertTrue((stage_root / "resources").is_dir(), stage)

        nested = list((PACKAGE_ROOT / "wf").glob("*/*/workflow.lgwf"))
        self.assertEqual([], nested)


if __name__ == "__main__":
    unittest.main()
