from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    PACKAGE_ROOT
    / "wf"
    / "04_confirm_business_flow"
    / "scripts"
    / "scaffold_package.py"
)
sys.dont_write_bytecode = True


def load_module():
    spec = importlib.util.spec_from_file_location("lgwf_wf_create_scaffold_package", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ScaffoldPackageRuleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_normalize_relative_path_rejects_invalid_paths(self) -> None:
        for raw in ("../bad", "C:/bad", "/bad", ".lgwf", "ws/.lgwf"):
            with self.assertRaises(ValueError):
                self.module.normalize_relative_path(raw)

    def test_normalize_relative_path_strips_surrounding_whitespace(self) -> None:
        self.assertEqual(
            self.module.normalize_relative_path("  skills/demo  "),
            "skills/demo",
        )

    def test_build_scaffold_plan_keeps_state_boundary_and_relative_paths(self) -> None:
        plan = self.module.build_scaffold_plan(
            {
                "workflow_name": "demo",
                "target_package_root": "skills/demo",
                "business_flow": {
                    "stages": [
                        {
                            "stage_id": "package_scaffold",
                            "key_nodes": ["scaffold_package"],
                            "human_approval": False,
                        }
                    ]
                },
            }
        )
        self.assertEqual(plan["target_package_root"], "skills/demo")
        self.assertEqual(plan["package_profile"], "internal_workflow_package")
        self.assertEqual(plan["template"]["template_id"], "workflow_packaged_skill")
        self.assertIn("只使用相对路径", plan["rules"]["path_policy"])
        self.assertIn("不向目标 package 根目录写入 `.lgwf`", plan["rules"]["state_boundary"])
        self.assertIn("wf/workflow.lgwf", plan["create_files"])
        self.assertIn("AGENTS.md", plan["create_files"])
        self.assertNotIn("SKILL.md", plan["create_files"])
        self.assertIn("wf/docs/steps", plan["create_dirs"])

    def test_build_scaffold_plan_enforces_two_layer_workflow_paths(self) -> None:
        plan = self.module.build_scaffold_plan(
            {
                "workflow_name": "demo",
                "target_package_root": "skills/demo",
                "business_flow": {"stages": []},
            }
        )
        all_paths = [*plan["create_dirs"], *plan["create_files"]]
        self.assertIn("wf/02_confirm_requirements/workflow.lgwf", plan["create_files"])
        self.assertNotIn("wf/02_confirm_requirements/00_collect_raw_intent/workflow.lgwf", all_paths)
        self.assertFalse(any(path.startswith("wf/tests") for path in all_paths))
        self.assertFalse(
            any(
                path.startswith("wf/")
                and path.endswith("/workflow.lgwf")
                and len(Path(path).parts) > 3
                for path in all_paths
            )
        )

    def test_build_scaffold_plan_can_generate_skill_wrapped_workflow_profile(self) -> None:
        plan = self.module.build_scaffold_plan(
            {
                "workflow_name": "demo",
                "target_package_root": "skills/demo",
                "package_profile": "skill_wrapped_workflow",
                "business_flow": {"stages": []},
            }
        )
        self.assertEqual(plan["package_profile"], "skill_wrapped_workflow")
        self.assertIn("SKILL.md", plan["create_files"])
        self.assertIn("AGENTS.md", plan["create_files"])
        self.assertIn("wf/workflow.lgwf", plan["create_files"])
        self.assertIn("SKILL.md", plan["placeholders"])

    def test_build_scaffold_plan_rejects_unknown_profile(self) -> None:
        with self.assertRaises(ValueError):
            self.module.build_scaffold_plan(
                {
                    "workflow_name": "demo",
                    "target_package_root": "skills/demo",
                    "package_profile": "unknown",
                    "business_flow": {"stages": []},
                }
            )

    def test_build_scaffold_plan_exposes_result_contract_without_root_state_files(self) -> None:
        plan = self.module.build_scaffold_plan(
            {
                "workflow_name": "demo",
                "target_package_root": "skills/demo",
                "business_flow": {
                    "stages": [
                        {
                            "stage_id": "package_scaffold",
                            "key_nodes": ["scaffold_package", "summarize_create_result"],
                            "human_approval": False,
                        }
                    ]
                },
            }
        )
        self.assertEqual(
            plan["derived_from_business_flow"],
            [
                {
                    "stage_id": "package_scaffold",
                    "key_nodes": ["scaffold_package", "summarize_create_result"],
                    "human_approval": False,
                }
            ],
        )
        self.assertIn("tests/README.md", plan["create_files"])
        self.assertIn("ws", plan["placeholders"])
        self.assertIn("ws/.lgwf", plan["placeholders"]["ws"])
        self.assertIn("wf", plan["placeholders"])
        self.assertFalse(any(path.startswith(".lgwf") for path in plan["create_dirs"]))
        self.assertFalse(any(path.startswith(".lgwf") for path in plan["create_files"]))

    def test_build_scaffold_plan_validates_generated_paths(self) -> None:
        self.assertTrue(
            self.module.validate_plan_paths(
                {
                    "create_dirs": ["agents", "docs/steps"],
                    "create_files": ["wf/workflow.lgwf", "tests/README.md"],
                }
            )
        )
        with self.assertRaises(ValueError):
            self.module.validate_plan_paths({"create_dirs": ["agents"], "create_files": ["C:/bad"]})
        with self.assertRaises(ValueError):
            self.module.validate_plan_paths(
                {
                    "create_dirs": ["wf/demo/sub"],
                    "create_files": ["wf/demo/sub/workflow.lgwf"],
                }
            )


if __name__ == "__main__":
    unittest.main()
