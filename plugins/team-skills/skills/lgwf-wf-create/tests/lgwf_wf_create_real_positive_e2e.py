from __future__ import annotations

import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_LGWF = PACKAGE_ROOT / "wf" / "workflow.lgwf"


class LgwfWfCreateRealPositiveE2ETest(unittest.TestCase):
    def test_real_positive_entrypoint_is_explicit_and_targets_create_workflow(self) -> None:
        self.assertTrue(WORKFLOW_LGWF.exists())
        workflow_text = WORKFLOW_LGWF.read_text(encoding="utf-8")
        self.assertIn("WORKFLOW lgwf_wf_create;", workflow_text)
        self.assertIn("ENTRY define_requirements;", workflow_text)
        self.assertIn("summarize_create_result", workflow_text)


if __name__ == "__main__":
    unittest.main()
