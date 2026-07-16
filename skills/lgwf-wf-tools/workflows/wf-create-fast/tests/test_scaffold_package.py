from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    PACKAGE_ROOT
    / "wf"
    / "02_confirm_business_flow"
    / "03_scaffold_package"
    / "scripts"
    / "scaffold_package.py"
)


def load_scaffold_module():
    spec = importlib.util.spec_from_file_location("wf_create_fast_scaffold_package", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScaffoldPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_scaffold_module()

    def test_build_plan_allows_absolute_target_package_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target_root = str(Path(tmp) / "target-workflow")
            plan = self.module.build_scaffold_plan(
                {
                    "workflow_name": "demo-workflow",
                    "target_package_root": target_root,
                    "business_flow": {
                        "stages": [
                            {"stage_id": "prepare", "key_nodes": ["prepare_data"]},
                        ]
                    },
                }
            )

        self.assertEqual(plan["target_package_root"], target_root)
        self.assertIn("wf/01_prepare/workflow.lgwf", plan["create_files"])

    def test_target_root_rejects_runtime_and_parent_paths(self) -> None:
        for raw_path in ("../outside", "inside/.lgwf/state", "https://example.com/workflow"):
            with self.subTest(raw_path=raw_path):
                with self.assertRaises(ValueError):
                    self.module.normalize_target_package_root(raw_path)


if __name__ == "__main__":
    unittest.main()
