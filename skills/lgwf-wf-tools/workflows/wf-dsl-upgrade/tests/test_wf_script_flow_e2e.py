from __future__ import annotations

import py_compile
import re
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
        self.assertIn('PERSIST ".lgwf/scope_approval.json"', text)
        self.assertIn("WRITE state.wf_dsl_upgrade.scope_approval", text)

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
