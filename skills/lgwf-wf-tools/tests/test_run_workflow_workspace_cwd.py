from __future__ import annotations

import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
VENDOR_SCRIPTS = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts"
if str(VENDOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDOR_SCRIPTS))

import run_workflow  # noqa: E402


def load_lgwf_script():
    module_path = VENDOR_SCRIPTS / "lgwf.py"
    spec = importlib.util.spec_from_file_location("lgwf_facade_script_for_test", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 lgwf.py: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lgwf = load_lgwf_script()


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

    def test_run_workflow_resolves_workflows_relative_to_skill_root_from_other_cwd(self) -> None:
        workflow = FACADE_ROOT / "workflows" / "wf-convert" / "wf" / "workflow.lgwf"
        self.assertTrue(workflow.is_file())

        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                Path(tmp).mkdir(parents=True, exist_ok=True)
                import os

                os.chdir(tmp)
                self.assertEqual(
                    run_workflow._workflow_workspace_cwd("workflows/wf-convert/wf/workflow.lgwf"),
                    FACADE_ROOT.resolve(),
                )
            finally:
                os.chdir(previous)

    def test_lgwf_resolves_workflows_relative_to_skill_root_from_other_cwd(self) -> None:
        workflow = FACADE_ROOT / "workflows" / "wf-convert" / "wf" / "workflow.lgwf"
        self.assertTrue(workflow.is_file())

        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                Path(tmp).mkdir(parents=True, exist_ok=True)
                import os

                os.chdir(tmp)
                self.assertEqual(
                    lgwf._workflow_workspace_cwd("workflows/wf-convert/wf/workflow.lgwf"),
                    FACADE_ROOT.resolve(),
                )
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
