from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "skills"
FACADE_ROOT = SKILLS_ROOT / "lgwf-wf-tools"
MODULE_CONTRACT = FACADE_ROOT / "workflows" / "01-share" / "module-contract.md"
REGISTRY = FACADE_ROOT / "registry.json"


class ModuleContractsTest(unittest.TestCase):
    def test_shared_module_contract_defines_supported_module_types(self) -> None:
        text = MODULE_CONTRACT.read_text(encoding="utf-8")

        for module_type in ("codex_skill", "lgwf_workflow_package", "tool_workflow"):
            self.assertIn(module_type, text)

        for required_topic in ("模块定位", "入口", "依赖", "状态", "产物", "验证", "禁止"):
            self.assertIn(required_topic, text)

    def test_every_skill_has_self_contained_entry_docs(self) -> None:
        for skill_root in sorted(path for path in SKILLS_ROOT.iterdir() if path.is_dir()):
            with self.subTest(skill=skill_root.name):
                self.assertTrue((skill_root / "SKILL.md").is_file())
                self.assertTrue((skill_root / "AGENTS.md").is_file())
                self.assertTrue((skill_root / "README.md").is_file())

                agents_text = (skill_root / "AGENTS.md").read_text(encoding="utf-8")
                for required_topic in ("模块类型", "模块定位", "入口", "依赖", "状态边界", "验证", "禁止事项"):
                    self.assertIn(required_topic, agents_text)

                if (skill_root / "wf").is_dir():
                    self.assertTrue((skill_root / "wf" / "workflow.lgwf").is_file())
                    self.assertTrue((skill_root / "ws").is_dir())

    def test_lgwf_wf_tools_registry_workflows_reference_module_contract(self) -> None:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for workflow in registry["workflows"]:
            agents_md = FACADE_ROOT / workflow["agents_md"]
            with self.subTest(workflow=workflow["id"]):
                text = agents_md.read_text(encoding="utf-8")
                self.assertIn("module-contract.md", text)
                if workflow["kind"] == "lgwf":
                    self.assertIn("lgwf_workflow_package", text)
                else:
                    self.assertIn("tool_workflow", text)


if __name__ == "__main__":
    unittest.main()
