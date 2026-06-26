from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
LGWF_PLAN_ROOT = ROOT / "plugins" / "team-skills" / "skills" / "lgwf-plan"
PACKAGE_ROOT = ROOT / "plugins" / "team-skills" / "skills" / "lgwf-wf-create"
SCAFFOLD_RESULT = LGWF_PLAN_ROOT / ".tmp" / "lgwf-wf-create-plan" / ".lgwf" / "scaffold_result.json"
STEP_DIRS = (
    "00_collect_raw_intent",
    "01_propose_requirements_react",
    "02_confirm_requirements",
    "03_propose_business_flow_react",
    "04_confirm_business_flow",
    "05_scaffold_package",
    "06_design_steps_react",
    "07_confirm_step_designs",
    "08_implement_steps_react",
    "09_summarize_create_result",
)
PRIVATE_SLOT_NAMES = ("agents", "scripts", "resources", "tests")


class WorkflowCreateScaffoldContractTest(unittest.TestCase):
    def test_package_entry_files_exist(self) -> None:
        for name in ("SKILL.md", "README.md", "workflow.lgwf"):
            self.assertTrue((PACKAGE_ROOT / name).is_file(), name)

    def test_package_core_dirs_exist(self) -> None:
        for relative in ("shared", "docs/steps", "tests"):
            self.assertTrue((PACKAGE_ROOT / relative).is_dir(), relative)
        for step_dir in STEP_DIRS:
            self.assertTrue((PACKAGE_ROOT / step_dir).is_dir(), step_dir)

    def test_each_step_dir_has_private_resource_slot(self) -> None:
        for step_dir in STEP_DIRS:
            root = PACKAGE_ROOT / step_dir
            present = [name for name in PRIVATE_SLOT_NAMES if (root / name).is_dir()]
            self.assertTrue(present, f"{step_dir} 缺少私有资源位点")
            files = [path for path in root.rglob("*") if path.is_file()]
            self.assertTrue(files, f"{step_dir} 不应为空壳目录")

    def test_workflow_uses_only_relative_paths(self) -> None:
        text = (PACKAGE_ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertNotIn("..", text)
        self.assertIsNone(re.search(r"[A-Za-z]:\\\\", text))
        self.assertIsNone(re.search(r"\b(?:https?|file)://", text))
        self.assertIn('PROMPT_REF "00_collect_raw_intent/confirm_raw_intent.md"', text)
        self.assertIn('SCRIPT "05_scaffold_package/scripts/scaffold_package.py"', text)
        self.assertIn('PROMPT "08_implement_steps_react/agents/act.md"', text)

    def test_package_has_no_runtime_pollution(self) -> None:
        forbidden = {".tmp", "__pycache__", ".lgwf"}
        for path in PACKAGE_ROOT.rglob("*"):
            self.assertNotIn(path.name, forbidden, path)

    def test_scaffold_result_records_tree_and_checks(self) -> None:
        self.assertTrue(SCAFFOLD_RESULT.is_file())
        data = json.loads(SCAFFOLD_RESULT.read_text(encoding="utf-8"))
        self.assertEqual(data["task_id"], "scaffold_workflow_package")
        self.assertEqual(data["target_package_root"], "plugins/team-skills/skills/lgwf-wf-create")
        self.assertEqual(data["step_directories"], list(STEP_DIRS))
        self.assertIn("tree", data)
        self.assertIn("checks", data)
        for check_id in (
            "check_scaffold_core_files",
            "check_scaffold_step_private_slots",
            "check_scaffold_workflow_relative_paths",
            "check_scaffold_result_recorded",
            "check_scaffold_no_runtime_pollution",
        ):
            self.assertIn(check_id, data["checks"])


if __name__ == "__main__":
    unittest.main()
