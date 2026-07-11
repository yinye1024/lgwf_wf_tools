from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = PACKAGE_ROOT / "wf"


class RepoContextPackWorkflowStructureTests(unittest.TestCase):
    def test_required_package_files_exist(self) -> None:
        for relative in (
            "SKILL.md",
            "AGENTS.md",
            "README.md",
            "entry_contract.json",
            "scripts/build_context_pack.py",
            "wf/workflow.lgwf",
            "wf/artifact_contracts.json",
            "wf/shared/scripts/repo_context_runtime.py",
        ):
            self.assertTrue((PACKAGE_ROOT / relative).is_file(), relative)

    def test_workflow_has_only_allowed_workflow_roots(self) -> None:
        workflow_files = sorted(path.relative_to(PACKAGE_ROOT).as_posix() for path in PACKAGE_ROOT.rglob("workflow.lgwf"))
        self.assertIn("wf/workflow.lgwf", workflow_files)
        self.assertNotIn("workflow.lgwf", workflow_files)
        for relative in workflow_files:
            parts = Path(relative).parts
            self.assertTrue(
                relative == "wf/workflow.lgwf" or (len(parts) == 3 and parts[0] == "wf" and parts[2] == "workflow.lgwf"),
                relative,
            )

    def test_root_workflow_references_four_stage_workflows(self) -> None:
        text = (WORKFLOW_ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        for stage in (
            "entry_scope_resolution",
            "target_context_inventory",
            "context_pack_rendering",
            "workflow_summary_handoff",
        ):
            self.assertIn(f'WORKFLOW "{stage}/workflow.lgwf"', text)
            self.assertTrue((WORKFLOW_ROOT / stage / "workflow.lgwf").is_file(), stage)
            self.assertTrue((WORKFLOW_ROOT / stage / "agents" / "prompt.md").is_file(), stage)
            self.assertTrue((WORKFLOW_ROOT / stage / "scripts" / "run.py").is_file(), stage)

    def test_resource_paths_are_relative(self) -> None:
        pattern = re.compile(r'"([^"]+)"')
        for workflow in WORKFLOW_ROOT.rglob("workflow.lgwf"):
            text = workflow.read_text(encoding="utf-8")
            for value in pattern.findall(text):
                if "/" not in value and "\\" not in value:
                    continue
                self.assertFalse(Path(value).is_absolute(), value)
                self.assertNotIn("..", Path(value.replace("\\", "/")).parts, value)
                self.assertNotRegex(value, r"^[A-Za-z]:", value)

    def test_entry_contract_keeps_target_read_only(self) -> None:
        contract = json.loads((PACKAGE_ROOT / "entry_contract.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["state_boundary"]["target_dir_access"], "read_only")
        self.assertNotIn("output_dir", contract["input_schema"]["required"])
        self.assertEqual(contract["workflow_lgwf"], "wf/workflow.lgwf")
        self.assertEqual(contract["work_dir"], "ws")


if __name__ == "__main__":
    unittest.main()
