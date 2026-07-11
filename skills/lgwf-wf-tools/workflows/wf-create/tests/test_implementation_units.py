from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WF_ROOT = PACKAGE_ROOT / "wf"
IMPLEMENT_ROOT = WF_ROOT / "04_implement_steps_react"


def load_module(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, IMPLEMENT_ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ImplementationUnitScriptsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prepare_units = load_module("scripts/prepare_implementation_units.py", "prepare_implementation_units")
        cls.prepare_current = load_module(
            "scripts/prepare_current_implementation_unit.py",
            "prepare_current_implementation_unit",
        )
        cls.merge_units = load_module("scripts/merge_implementation_results.py", "merge_implementation_results")

    def seed_context(self, root: Path, observe: dict[str, object] | None = None) -> Path:
        target_package = root / "workspace" / "skills" / "demo-workflow"
        lgwf_dir = root / ".lgwf"
        lgwf_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            lgwf_dir / "implementation_context.json",
            {
                "workflow_name": "demo_workflow",
                "workspace_root": str((root / "workspace").resolve()),
                "work_dir": str(root.resolve()),
                "target_package_root": "skills/demo-workflow",
                "target_package_abs": str(target_package.resolve()),
                "package_profile": "internal_workflow_package",
            },
        )
        write_json(
            lgwf_dir / "step_designs.json",
            {
                "confirmed": {
                    "workflow_name": "demo_workflow",
                    "source_business_flow_stages": [
                        {"stage_id": "01_collect_context"},
                        {"stage_id": "02_run_checks"},
                    ],
                    "step_designs": [
                        {
                            "step_slug": "collect_context",
                            "stage_id": "01_collect_context",
                            "doc_path": "docs/steps/collect-context.md",
                        },
                        {
                            "step_slug": "run_checks",
                            "stage_id": "02_run_checks",
                            "doc_path": "docs/steps/run-checks.md",
                        },
                    ],
                }
            },
        )
        (lgwf_dir / "implementation_reason.md").write_text("本轮实现全部已确认阶段。", encoding="utf-8")
        write_json(
            lgwf_dir / "implementation_observe.json",
            observe
            or {
                "initial": True,
                "passed": False,
                "failures": ["首轮尚未执行 authoring audit"],
            },
        )
        return target_package

    def test_initial_prepare_generates_disjoint_units(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)

            result = self.prepare_units.build_implementation_units(root)
            units = result["implementation_units"]
            unit_ids = [unit["unit_id"] for unit in units]

            self.assertEqual(result["selection_mode"], "full")
            self.assertIn("package_contracts", unit_ids)
            self.assertIn("root_workflow", unit_ids)
            self.assertIn("stage_01_collect_context", unit_ids)
            self.assertIn("stage_02_run_checks", unit_ids)
            self.assertIn("shared_helpers_tests", unit_ids)

            all_files = [path for unit in units for path in unit["target_files"]]
            self.assertEqual(len(all_files), len(set(all_files)))
            self.assertTrue(all(Path(path).is_absolute() for path in all_files))
            self.assertIn(str((target_package / "wf" / "workflow.lgwf").resolve()), all_files)
            self.assertTrue((root / ".lgwf" / "implementation_units.json").is_file())

    def test_prepare_uses_observe_failures_to_select_affected_units(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(
                root,
                {
                    "passed": False,
                    "failures": ["wf\\02_run_checks\\workflow.lgwf 不存在"],
                },
            )

            result = self.prepare_units.build_implementation_units(root)
            unit_ids = [unit["unit_id"] for unit in result["implementation_units"]]

            self.assertEqual(result["selection_mode"], "repair")
            self.assertIn("stage_02_run_checks", unit_ids)
            self.assertNotIn("stage_01_collect_context", unit_ids)

    def test_merge_records_foreach_collected_failures_with_unit_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            result = self.merge_units.merge_implementation_results(
                root,
                {
                    "unit_results": [
                        {
                            "status": "failed",
                            "index": 1,
                            "item": {"unit_id": "stage_02_run_checks"},
                            "message": "child workflow failed",
                        }
                    ]
                },
            )

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failed_units"], ["stage_02_run_checks"])
            self.assertEqual(result["unit_results"][0]["foreach_index"], 1)
            self.assertEqual(result["unit_results"][0]["remaining_risks"], ["child workflow failed"])

    def test_merge_accepts_foreach_results_object_container(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            result = self.merge_units.merge_implementation_results(
                root,
                {
                    "items": [
                        {
                            "status": "completed",
                            "index": 0,
                            "item": {"unit_id": "package_contracts"},
                            "output": {
                                "unit_id": "package_contracts",
                                "status": "ok",
                                "generated_files": [{"path": "AGENTS.md"}],
                            },
                        }
                    ]
                },
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["unit_count"], 1)
            self.assertEqual(result["unit_results"][0]["unit_id"], "package_contracts")

    def test_prepare_current_unit_materializes_child_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            unit = {
                "unit_id": "stage_01_collect_context",
                "unit_type": "stage",
                "target_files": [str((target_package / "wf" / "01_collect_context" / "workflow.lgwf").resolve())],
                "target_dirs": [str((target_package / "wf" / "01_collect_context").resolve())],
            }

            result = self.prepare_current.build_current_implementation_unit_context(root, unit)

            self.assertEqual(result["current_implementation_unit"]["unit_id"], "stage_01_collect_context")
            self.assertEqual(result["current_implementation_unit_target_files"], unit["target_files"])
            self.assertTrue((root / ".lgwf" / "current_implementation_unit_context.json").is_file())

    def test_merge_preserves_validation_and_summary_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            unit_results = [
                {
                    "unit_id": "package_contracts",
                    "status": "ok",
                    "generated_files": [{"path": "AGENTS.md"}, {"path": "README.md"}],
                    "generated": {"root_files": ["AGENTS.md", "README.md"]},
                },
                {
                    "unit_id": "stage_01_collect_context",
                    "status": "ok",
                    "generated_files": ["wf/01_collect_context/workflow.lgwf"],
                    "generated": {
                        "by_step": [
                            {
                                "step_slug": "collect_context",
                                "generated_files": ["wf/01_collect_context/workflow.lgwf"],
                            }
                        ]
                    },
                },
            ]

            result = self.merge_units.merge_implementation_results(root, {"unit_results": unit_results})

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["workflow_name"], "demo_workflow")
            self.assertEqual(result["target_package_root"], "skills/demo-workflow")
            self.assertEqual(
                [item["path"] for item in result["generated_files"]],
                ["AGENTS.md", "README.md", "wf/01_collect_context/workflow.lgwf"],
            )
            self.assertEqual(result["generated"]["root_files"], ["AGENTS.md", "README.md"])
            self.assertEqual(
                result["generated"]["by_step"][0]["generated_files"],
                ["wf/01_collect_context/workflow.lgwf"],
            )
            self.assertTrue((root / ".lgwf" / "implementation_result.json").is_file())


if __name__ == "__main__":
    unittest.main()
