from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


FACADE_ROOT = Path(__file__).resolve().parents[1]
VENDOR_SCRIPTS = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts"
if str(VENDOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDOR_SCRIPTS))

from lgwf_env_init import existing_workflow  # noqa: E402


class ExistingWorkflowRerunCleanupTests(unittest.TestCase):
    def test_rerun_existing_recreates_missing_work_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "ws"
            args = SimpleNamespace(
                work_dir=str(work_dir),
                rerun_existing=True,
                continue_existing=False,
                resume_existing=False,
            )
            support = SimpleNamespace(workspace_layout=SimpleNamespace(lgwf_dir=lambda path: Path(path) / ".lgwf"))

            result = existing_workflow.handle_existing_workflow_data(args, io.StringIO(), io.StringIO(), support)

            self.assertIsNone(result)
            self.assertTrue(work_dir.is_dir())

    def test_delete_existing_lgwf_data_keeps_work_dir_and_non_lgwf_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "ws"
            lgwf_dir = work_dir / ".lgwf"
            workflow_dir = lgwf_dir / "workflow"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "workflow.json").write_text("{}", encoding="utf-8")
            user_file = work_dir / "input.json"
            user_file.write_text('{"repo_path":"."}', encoding="utf-8")
            support = SimpleNamespace(workspace_layout=SimpleNamespace(lgwf_dir=lambda path: Path(path) / ".lgwf"))

            existing_workflow.delete_existing_lgwf_data(work_dir, io.StringIO(), support)

            self.assertTrue(work_dir.is_dir())
            self.assertFalse(lgwf_dir.exists())
            self.assertTrue(user_file.exists())
            self.assertEqual('{"repo_path":"."}', user_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
