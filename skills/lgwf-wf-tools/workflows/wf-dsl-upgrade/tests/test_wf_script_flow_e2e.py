from __future__ import annotations

import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WF_ROOT = PACKAGE_ROOT / "wf"
TEXT_SUFFIXES = {".py", ".md", ".json", ".lgwf"}


class ScriptFlowE2ETest(unittest.TestCase):
    def workflow_files(self) -> list[Path]:
        return sorted(WF_ROOT.rglob("workflow.lgwf"))

    def text_files(self) -> list[Path]:
        return [
            path
            for path in PACKAGE_ROOT.rglob("*")
            if path.is_file()
            and path.suffix in TEXT_SUFFIXES
            and path.resolve() != Path(__file__).resolve()
            and ".lgwf" not in path.parts
            and "__pycache__" not in path.parts
        ]

    def test_all_workflow_files_exist_and_compile_script_refs(self) -> None:
        workflows = self.workflow_files()
        self.assertEqual(len(workflows), 5)
        compiled_scripts: set[Path] = set()
        for workflow in workflows:
            text = workflow.read_text(encoding="utf-8")
            for script_ref in re.findall(r'SCRIPT "([^"]+)"', text):
                with self.subTest(workflow=workflow.relative_to(PACKAGE_ROOT), script=script_ref):
                    self.assertFalse(Path(script_ref).is_absolute())
                    self.assertNotIn("..", Path(script_ref).parts)
                    script_path = workflow.parent / script_ref
                    self.assertTrue(script_path.exists(), script_path)
                    compiled_scripts.add(script_path)
        self.assertTrue(compiled_scripts)
        for script_path in sorted(compiled_scripts):
            with self.subTest(script=script_path.relative_to(PACKAGE_ROOT)):
                py_compile.compile(str(script_path), doraise=True)

    def test_per_target_scripts_import_from_standalone_child_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = WF_ROOT / "03_upgrade_one_target"
            child_root = Path(temp_dir) / "03_upgrade_one_target"
            shutil.copytree(source, child_root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            code = r'''
import importlib.util
import sys
from pathlib import Path

root = Path(sys.argv[1])
scripts = sorted(path for path in (root / "scripts").glob("*.py") if path.name != "__init__.py")
for index, script in enumerate(scripts):
    spec = importlib.util.spec_from_file_location(f"standalone_child_script_{index}", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
print(f"imported {len(scripts)} scripts")
'''
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            completed = subprocess.run(
                [sys.executable, "-c", code, str(child_root)],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_nested_workflow_and_prompt_refs_are_package_relative(self) -> None:
        for workflow in self.workflow_files():
            text = workflow.read_text(encoding="utf-8")
            for pattern in (r'WORKFLOW "([^"]+)"', r'PROMPT_REF "([^"]+)"'):
                for ref in re.findall(pattern, text):
                    with self.subTest(workflow=workflow.relative_to(PACKAGE_ROOT), ref=ref):
                        self.assertFalse(Path(ref).is_absolute())
                        self.assertNotIn("..", Path(ref).parts)
                        self.assertTrue((workflow.parent / ref).exists(), ref)

    def test_route_contracts_are_declared(self) -> None:
        root_workflow = (WF_ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ROUTE select_scope_branch READ state.wf_dsl_upgrade.scope_route", root_workflow)
        self.assertIn('WHEN "run" THEN upgrade_followup', root_workflow)
        self.assertIn('WHEN "summary" THEN summarize_upgrade_result', root_workflow)
        self.assertIn("FOREACH upgrade_each", root_workflow)
        self.assertIn('RUN_WORKFLOW "03_upgrade_one_target/workflow.lgwf"', root_workflow)

        confirm_workflow = (WF_ROOT / "02_confirm_scope" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("APPROVAL confirm_scope", confirm_workflow)
        self.assertIn("READ state.wf_dsl_upgrade.scope_confirmation_context", confirm_workflow)
        self.assertIn("WRITE state.wf_dsl_upgrade.scope_approval", confirm_workflow)
        self.assertIn("PY prepare_scope_route", confirm_workflow)

    def test_scope_gate_persists_scope_approval(self) -> None:
        text = (WF_ROOT / "02_confirm_scope" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("APPROVAL confirm_scope", text)
        self.assertIn("ROUTE_ON_DECISION", text)
        self.assertIn('PERSIST ".lgwf/scope_approval.json"', text)
        self.assertIn("RESULT state.wf_dsl_upgrade.confirm_scope_result", text)
        self.assertIn("WRITE state.wf_dsl_upgrade.scope_approval", text)

    def test_summary_receives_object_input_not_target_results_list(self) -> None:
        text = (WF_ROOT / "04_summarize_upgrade_result" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("INPUT state.wf_dsl_upgrade", text)
        self.assertNotIn("INPUT state.wf_dsl_upgrade.target_results", text)

    def test_source_tree_has_no_generated_isolation_or_local_absolute_paths(self) -> None:
        local_repo_root = PACKAGE_ROOT.parents[3]
        forbidden = [
            "/".join(["wf-post-fix", "ws", ".lgwf", "isolations"]),
            str(local_repo_root).replace("\\", "/"),
            str(local_repo_root),
        ]
        for path in self.text_files():
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                with self.subTest(path=path.relative_to(PACKAGE_ROOT), pattern=pattern):
                    self.assertNotIn(pattern, text)


if __name__ == "__main__":
    unittest.main()
