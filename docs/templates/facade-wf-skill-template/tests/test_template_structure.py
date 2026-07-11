from __future__ import annotations

import json
import unittest
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
SKELETON_ROOT = TEMPLATE_ROOT / "skeleton"


class FacadeWfSkillTemplateTests(unittest.TestCase):
    def test_required_template_files_exist(self) -> None:
        required = [
            "README.md",
            "agent-migration-prompt.md",
            "migration-guide.md",
            "adaptation-notes.md",
            "skeleton/SKILL.md",
            "skeleton/AGENTS.md",
            "skeleton/README.md",
            "skeleton/registry.json",
            "skeleton/docs/maintenance.md",
            "skeleton/docs/workflow-routing.md",
            "skeleton/docs/workflow-inputs.md",
            "skeleton/docs/facade-dispatch.md",
            "skeleton/workflows/01-share/module-contract.md",
            "skeleton/workflows/01-share/registry-contract.md",
            "skeleton/workflows/01-share/entry-contract.md",
            "skeleton/workflows/01-share/approval.md",
            "skeleton/workflows/01-share/artifacts.md",
            "skeleton/workflows/example-workflow/AGENTS.md",
            "skeleton/workflows/example-workflow/README.md",
            "skeleton/workflows/example-workflow/entry_contract.json",
            "skeleton/workflows/example-workflow/wf/workflow.lgwf",
            "skeleton/workflows/example-workflow/wf/scripts/finish.py",
            "skeleton/workflows/example-workflow/ws/.gitkeep",
            "skeleton/workflows/example-tool-workflow/AGENTS.md",
            "skeleton/workflows/example-tool-workflow/README.md",
            "skeleton/workflows/example-tool-workflow/entry_contract.json",
            "skeleton/workflows/example-tool-workflow/scripts/example_tool.py",
            "skeleton/scripts/list_workflows.py",
            "skeleton/scripts/validate_registry.py",
            "skeleton/scripts/run_skill_workflow.py",
            "skeleton/tests/test_registry_template.py",
        ]
        missing = [path for path in required if not (TEMPLATE_ROOT / path).is_file()]
        self.assertEqual(missing, [])

    def test_skeleton_registry_declares_lgwf_and_tool_workflow_examples(self) -> None:
        registry_path = SKELETON_ROOT / "registry.json"
        self.assertTrue(registry_path.is_file(), f"missing registry: {registry_path}")
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        workflows = {item["id"]: item for item in registry["workflows"]}
        self.assertEqual(set(workflows), {"example-workflow", "example-tool-workflow"})
        self.assertEqual(workflows["example-workflow"]["kind"], "lgwf")
        self.assertEqual(workflows["example-tool-workflow"]["kind"], "tool-workflow")


if __name__ == "__main__":
    unittest.main()
