from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
VENDOR_SCRIPTS = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts"
if str(VENDOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDOR_SCRIPTS))

import lgwf  # noqa: E402
import run_workflow  # noqa: E402


class RunWorkflowWorkspaceCwdTests(unittest.TestCase):
    def test_run_workflow_infers_workspace_root_from_workflows_segment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "skill-root"
            workflow = workspace / "workflows" / "parent" / "wf" / "workflow.lgwf"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("WORKFLOW parent;\n", encoding="utf-8")

            self.assertEqual(run_workflow._workflow_workspace_cwd(str(workflow)), workspace.resolve())

    def test_lgwf_audit_compile_use_same_workspace_root_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "skill-root"
            workflow = workspace / "workflows" / "parent" / "wf" / "workflow.lgwf"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("WORKFLOW parent;\n", encoding="utf-8")

            self.assertEqual(lgwf._workflow_workspace_cwd(str(workflow)), workspace.resolve())


if __name__ == "__main__":
    unittest.main()
