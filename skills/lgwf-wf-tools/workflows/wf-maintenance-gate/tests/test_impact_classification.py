from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SHARED = PACKAGE_ROOT / "wf" / "shared" / "scripts"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from maintenance_gate_common import classify_path, find_workspace_root


class ImpactClassificationTests(unittest.TestCase):
    def test_registry_json_is_high_risk_facade_entry(self) -> None:
        result = classify_path(
            "skills/lgwf-wf-tools/registry.json",
            ["wf-create", "wf-maintenance-gate"],
        )
        self.assertEqual(result["category"], "facade_entry")
        self.assertEqual(result["risk"], "high")
        self.assertIn("doctor_basic", result["recommended_checks"])

    def test_workflow_source_extracts_workflow_id(self) -> None:
        result = classify_path(
            "skills/lgwf-wf-tools/workflows/wf-create/wf/workflow.lgwf",
            ["wf-create"],
        )
        self.assertEqual(result["category"], "workflow_source")
        self.assertEqual(result["impacted_workflows"], ["wf-create"])

    def test_vendor_path_keeps_high_risk(self) -> None:
        result = classify_path(
            "skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py",
            ["wf-create"],
        )
        self.assertEqual(result["category"], "vendor")
        self.assertEqual(result["risk"], "high")

    def test_docs_only_is_low_priority_fallback(self) -> None:
        result = classify_path("docs/notes.md", ["wf-create"])
        self.assertEqual(result["category"], "docs_only")
        self.assertEqual(result["risk"], "low")

    def test_find_workspace_root_prefers_git_root_over_facade_nested_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir()
            facade = repo / "skills" / "lgwf-wf-tools"
            work_dir = facade / "workflows" / "wf-maintenance-gate" / "ws"
            work_dir.mkdir(parents=True)
            (facade / "skills").mkdir()
            self.assertEqual(repo.resolve(), find_workspace_root(work_dir))


if __name__ == "__main__":
    unittest.main()
