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
        cls.publish_current = load_module(
            "scripts/publish_current_implementation_unit_result.py",
            "publish_current_implementation_unit_result",
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
                        {"stage_id": "collect_context"},
                        {"stage_id": "run_checks"},
                    ],
                    "step_designs": [
                        {
                            "step_slug": "collect_context",
                            "stage_id": "collect_context",
                            "doc_path": "docs/steps/collect-context.md",
                        },
                        {
                            "step_slug": "run_checks",
                            "stage_id": "run_checks",
                            "doc_path": "docs/steps/run-checks.md",
                        },
                    ],
                }
            },
        )
        write_json(
            lgwf_dir / "scaffold_package_result.json",
            {
                "scaffold_plan": {
                    "workflow_name": "demo_workflow",
                    "target_package_root": "skills/demo-workflow",
                    "package_profile": "internal_workflow_package",
                    "stage_manifest": [
                        {
                            "stage_id": "collect_context",
                            "stage_dir": "01_collect_context",
                            "workflow_ref": "wf/01_collect_context/workflow.lgwf",
                        },
                        {
                            "stage_id": "run_checks",
                            "stage_dir": "02_run_checks",
                            "workflow_ref": "wf/02_run_checks/workflow.lgwf",
                        },
                    ],
                    "create_dirs": [
                        "scripts",
                        "tests",
                        "ws",
                        "wf",
                        "wf/shared/scripts",
                        "wf/docs/steps",
                        "wf/01_collect_context",
                        "wf/01_collect_context/agents",
                        "wf/01_collect_context/scripts",
                        "wf/01_collect_context/resources",
                        "wf/02_run_checks",
                        "wf/02_run_checks/agents",
                        "wf/02_run_checks/scripts",
                        "wf/02_run_checks/resources",
                    ],
                    "create_files": [
                        "AGENTS.md",
                        "README.md",
                        "entry_contract.json",
                        "wf/artifact_contracts.json",
                        "wf/workflow.lgwf",
                        "wf/01_collect_context/workflow.lgwf",
                        "wf/01_collect_context/agents/prompt.md",
                        "wf/01_collect_context/scripts/run.py",
                        "wf/01_collect_context/resources/README.md",
                        "wf/02_run_checks/workflow.lgwf",
                        "wf/02_run_checks/agents/prompt.md",
                        "wf/02_run_checks/scripts/run.py",
                        "wf/02_run_checks/resources/README.md",
                        "tests/README.md",
                        "tests/test_workflow_structure.py",
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
            package_unit = next(unit for unit in units if unit["unit_id"] == "package_contracts")
            root_unit = next(unit for unit in units if unit["unit_id"] == "root_workflow")
            stage_unit = next(unit for unit in units if unit["unit_id"] == "stage_01_collect_context")
            support_unit = next(unit for unit in units if unit["unit_id"] == "shared_helpers_tests")
            self.assertEqual(
                package_unit["package_relative_files"],
                ["AGENTS.md", "README.md", "entry_contract.json", "wf/artifact_contracts.json"],
            )
            self.assertEqual(package_unit["package_relative_dirs"], [".", "wf"])
            self.assertNotIn("scripts", package_unit["package_relative_dirs"])
            self.assertNotIn("ws", package_unit["package_relative_dirs"])
            self.assertNotIn("tests", package_unit["package_relative_dirs"])
            self.assertEqual(
                root_unit["package_relative_files"],
                ["wf/workflow.lgwf", "wf/docs/steps/collect-context.md", "wf/docs/steps/run-checks.md"],
            )
            self.assertEqual(root_unit["package_relative_dirs"], ["wf", "wf/docs/steps"])
            self.assertEqual(stage_unit["stage_id"], "collect_context")
            self.assertEqual(stage_unit["stage_dir"], "01_collect_context")
            self.assertEqual(stage_unit["workflow_ref"], "wf/01_collect_context/workflow.lgwf")
            self.assertIn("wf/01_collect_context/scripts/run.py", stage_unit["planned_files"])
            self.assertNotIn("wf", stage_unit["package_relative_dirs"])
            self.assertEqual(support_unit["package_relative_files"], ["tests/README.md", "tests/test_workflow_structure.py"])
            self.assertIn("scripts", support_unit["package_relative_dirs"])
            self.assertIn("ws", support_unit["package_relative_dirs"])
            self.assertIn("wf/shared/scripts", support_unit["package_relative_dirs"])
            self.assertNotIn("wf/01_collect_context", support_unit["package_relative_dirs"])

            all_files = [path for unit in units for path in unit["output_files"]]
            self.assertEqual(len(all_files), len(set(all_files)))
            self.assertTrue(all(not Path(path).is_absolute() for path in all_files))
            self.assertIn("wf/workflow.lgwf", all_files)
            self.assertTrue((root / ".lgwf" / "implementation_units.json").is_file())

    def test_prepare_uses_observe_failures_to_select_affected_units(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            missing_stage_workflow = target_package / "wf" / "02_run_checks" / "workflow.lgwf"
            failure = f"{missing_stage_workflow}:3:1 触发 DSL 语法错误"
            self.seed_context(
                root,
                {
                    "passed": False,
                    "failures": [failure],
                },
            )

            result = self.prepare_units.build_implementation_units(root)
            unit_ids = [unit["unit_id"] for unit in result["implementation_units"]]

            self.assertEqual(result["selection_mode"], "repair")
            self.assertIn("stage_02_run_checks", unit_ids)
            self.assertNotIn("stage_01_collect_context", unit_ids)

    def test_prepare_selects_root_workflow_without_package_contracts_for_root_workflow_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(
                root,
                {
                    "passed": False,
                    "failures": ["wf\\workflow.lgwf:3:1 触发 DSL 语法错误：Expected ';'。"],
                },
            )

            result = self.prepare_units.build_implementation_units(root)
            unit_ids = [unit["unit_id"] for unit in result["implementation_units"]]

            self.assertEqual(result["selection_mode"], "repair")
            self.assertEqual(unit_ids, ["root_workflow"])

    def test_prepare_selects_support_unit_for_unallocated_scaffold_dir_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(
                root,
                {
                    "passed": False,
                    "failures": ["scaffold_plan create_dir scripts 不存在"],
                },
            )

            result = self.prepare_units.build_implementation_units(root)
            unit_ids = [unit["unit_id"] for unit in result["implementation_units"]]

            self.assertEqual(result["selection_mode"], "repair")
            self.assertEqual(unit_ids, ["shared_helpers_tests"])

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
                "target_package_abs": str(target_package.resolve()),
                "workspace_root": str((root / "workspace").resolve()),
                "output_files": ["wf/01_collect_context/workflow.lgwf"],
                "output_dirs": ["wf/01_collect_context"],
            }

            result = self.prepare_current.build_current_implementation_unit_context(root, unit)

            self.assertEqual(result["current_implementation_unit"]["unit_id"], "stage_01_collect_context")
            self.assertNotIn("target_package_abs", result)
            self.assertNotIn("target_package_abs", result["current_implementation_unit"])
            self.assertNotIn("workspace_root", result["current_implementation_unit"])
            self.assertEqual(result["output_files"], unit["output_files"])
            self.assertEqual(result["unit_output_dir"], ".lgwf/implementation_stage/stage_01_collect_context")
            self.assertFalse((target_package / "wf" / "01_collect_context" / "workflow.lgwf").is_file())
            self.assertTrue((root / ".lgwf" / "implementation_stage" / "stage_01_collect_context").is_dir())
            self.assertTrue((root / ".lgwf" / "current_implementation_unit_context.json").is_file())

    def test_publish_current_unit_materializes_staging_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            unit = {
                "unit_id": "stage_01_collect_context",
                "unit_type": "stage",
                "target_package_abs": str(target_package.resolve()),
                "output_files": ["wf/01_collect_context/workflow.lgwf"],
                "output_dirs": ["wf/01_collect_context"],
            }
            context = self.prepare_current.build_current_implementation_unit_context(root, unit)
            staged = root / context["workspace_output_files"][0]
            staged.write_text("WORKFLOW collect_context;\n", encoding="utf-8")
            write_json(
                root / ".lgwf" / "current_implementation_unit_result.json",
                {
                    "unit_id": "stage_01_collect_context",
                    "status": "ok",
                    "generated_files": ["wf/01_collect_context/workflow.lgwf"],
                },
            )

            result = self.publish_current.publish_current_implementation_unit_result(root)

            target_file = target_package / "wf" / "01_collect_context" / "workflow.lgwf"
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["generated_files"], [{"path": "wf/01_collect_context/workflow.lgwf"}])
            self.assertTrue(target_file.is_file())
            self.assertEqual(target_file.read_text(encoding="utf-8"), "WORKFLOW collect_context;\n")

    def test_publish_current_unit_publishes_all_staged_manifest_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            unit = {
                "unit_id": "package_contracts",
                "unit_type": "package",
                "target_package_abs": str(target_package.resolve()),
                "output_files": ["AGENTS.md", "README.md"],
                "output_dirs": ["."],
            }
            context = self.prepare_current.build_current_implementation_unit_context(root, unit)
            (root / context["workspace_output_files"][0]).write_text("# Agents\n", encoding="utf-8")
            (root / context["workspace_output_files"][1]).write_text("# Readme\n", encoding="utf-8")
            write_json(
                root / ".lgwf" / "current_implementation_unit_result.json",
                {
                    "unit_id": "package_contracts",
                    "status": "ok",
                    "generated_files": ["AGENTS.md"],
                },
            )

            result = self.publish_current.publish_current_implementation_unit_result(root)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["generated_files"], [{"path": "AGENTS.md"}, {"path": "README.md"}])
            self.assertEqual((target_package / "AGENTS.md").read_text(encoding="utf-8"), "# Agents\n")
            self.assertEqual((target_package / "README.md").read_text(encoding="utf-8"), "# Readme\n")

    def test_publish_current_unit_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            unit = {
                "unit_id": "stage_01_collect_context",
                "target_package_abs": str(target_package.resolve()),
                "output_files": ["../escape.lgwf"],
                "output_dirs": ["wf/01_collect_context"],
            }

            with self.assertRaises(ValueError):
                self.prepare_current.build_current_implementation_unit_context(root, unit)

    def test_publish_current_unit_rejects_generated_file_outside_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            unit = {
                "unit_id": "stage_01_collect_context",
                "target_package_abs": str(target_package.resolve()),
                "output_files": ["wf/01_collect_context/workflow.lgwf"],
                "output_dirs": ["wf/01_collect_context"],
            }
            context = self.prepare_current.build_current_implementation_unit_context(root, unit)
            staged = root / context["workspace_output_files"][0]
            staged.write_text("WORKFLOW collect_context;\n", encoding="utf-8")
            write_json(
                root / ".lgwf" / "current_implementation_unit_result.json",
                {
                    "unit_id": "stage_01_collect_context",
                    "status": "ok",
                    "generated_files": ["wf/other/workflow.lgwf"],
                },
            )

            with self.assertRaises(ValueError):
                self.publish_current.publish_current_implementation_unit_result(root)

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
