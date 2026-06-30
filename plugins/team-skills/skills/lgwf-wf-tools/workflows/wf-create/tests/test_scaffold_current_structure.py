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


class ScaffoldCurrentStructureTest(unittest.TestCase):
    def setUp(self) -> None:
        TMP_ROOT.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(prefix="wf-create-scaffold-", dir=TMP_ROOT)
        self.work_dir = Path(self.temp_dir.name)
        self.workflow_root = self.work_dir / ".lgwf" / "workflow"
        shutil.copytree(SOURCE_WF_ROOT, self.workflow_root)
        lgwf = self.work_dir / ".lgwf"
        lgwf.mkdir(exist_ok=True)
        payload = {
            "confirmed": {
                "workflow_name": "git-diff-brief",
                "target_package_root": "plugins/team-skills/skills/git-diff-brief",
                "package_profile": "internal_workflow_package",
                "stages": [],
            }
        }
        (lgwf / "create_requirements.json").write_text(json.dumps(payload), encoding="utf-8")
        (lgwf / "business_flow.json").write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_scaffold_package_fails_when_current_structure_validator_is_missing(self) -> None:
        validator = self.workflow_root / "shared" / "scripts" / "validate_two_layer_workflow.py"
        self.assertTrue(validator.is_file())
        validator.unlink()

        completed = subprocess.run(
            [
                sys.executable,
                str(self.workflow_root / "04_confirm_business_flow" / "scripts" / "scaffold_package.py"),
            ],
            cwd=self.work_dir,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(".lgwf", completed.stderr)
        self.assertIn("workflow", completed.stderr)
        self.assertIn("shared", completed.stderr)
        self.assertNotIn("workflows/wf-create/scripts", completed.stderr.replace("\\", "/"))

    def test_wf_create_runtime_code_does_not_reference_legacy_validator_locations(self) -> None:
        offenders: list[str] = []
        for path in SOURCE_WF_ROOT.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "workflows/wf-create/scripts" in text or '".lgwf" / "scripts"' in text:
                offenders.append(path.relative_to(SOURCE_WF_ROOT).as_posix())
            if ".lgwf/scripts" in text.replace("\\", "/"):
                offenders.append(path.relative_to(SOURCE_WF_ROOT).as_posix())
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
