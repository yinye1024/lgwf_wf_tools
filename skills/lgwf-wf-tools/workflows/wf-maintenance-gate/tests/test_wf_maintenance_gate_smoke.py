from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_SCRIPTS = PACKAGE_ROOT / "wf" / "06_summarize_gate_result" / "scripts"
SHARED = PACKAGE_ROOT / "wf" / "shared" / "scripts"
for path in (SUMMARY_SCRIPTS, SHARED):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from build_summary import main as build_summary_main


class MaintenanceGateSmokeTests(unittest.TestCase):
    def test_build_summary_writes_summary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            lgwf_dir = work_dir / ".lgwf"
            lgwf_dir.mkdir()
            (lgwf_dir / "maintenance_gate_request.json").write_text(
                json.dumps({"scope": "smoke"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (lgwf_dir / "impact_classification.json").write_text(
                json.dumps({"risk": "low", "categories": ["docs_only"], "impacted_workflows": [], "ambiguities": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            (lgwf_dir / "verification_results.json").write_text(
                json.dumps({"commands": [], "skipped": [], "stopped_early": False}, ensure_ascii=False),
                encoding="utf-8",
            )
            (lgwf_dir / "failure_routes.json").write_text(
                json.dumps({"routes": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            previous = Path.cwd()
            os.chdir(work_dir)
            try:
                build_summary_main()
            finally:
                os.chdir(previous)
            summary = json.loads((lgwf_dir / "maintenance_gate_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "pass")
            self.assertIn("reports/wf-maintenance-gate/report.md", summary["artifact_paths"])


if __name__ == "__main__":
    unittest.main()
