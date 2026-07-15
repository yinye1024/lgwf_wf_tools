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
        cls.prepare_units = load_module(
            "01_implement_units/scripts/prepare_implementation_units.py",
            "prepare_implementation_units",
        )
        cls.prepare_current = load_module(
            "01_implement_units/01_implement_one_unit/scripts/prepare_current_implementation_unit.py",
            "prepare_current_implementation_unit",
        )
        cls.publish_current = load_module(
            "01_implement_units/01_implement_one_unit/scripts/publish_current_implementation_unit_result.py",
            "publish_current_implementation_unit_result",
        )
        cls.merge_units = load_module(
            "01_implement_units/scripts/merge_implementation_results.py",
            "merge_implementation_results",
        )
        cls.publish_repair = load_module(
            "02_repair_implementation_react/02_act_repair/scripts/publish_repair_result.py",
            "publish_repair_result",
        )

    def seed_context(self, root: Path) -> Path:
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
                    "target_package_root": "skills/demo-workflow",
                    "package_profile": "internal_workflow_package",
                    "source_business_flow_stages": [
                        {"stage_id": "collect_context"},
                        {"stage_id": "run_checks"},
                    ],
                    "step_designs": [
                        {
                            "step_slug": "collect_context",
                            "step_name": "收集上下文",
                            "stage_id": "collect_context",
                            "goal": "收集目标上下文。",
                            "inputs": [".lgwf/create_requirements.json"],
                            "outputs": [".lgwf/collect_context_result.json"],
                            "dependencies": [],
                            "implementation_suggestions": ["生成阶段 workflow 和私有资源。"],
                            "acceptance_notes": ["阶段目录自包含。"],
                            "out_of_scope": ["端到端运行保证"],
                            "confirmation_points": ["阶段边界正确"],
                            "target_files": [
                                "AGENTS.md",
                                "README.md",
                                "entry_contract.json",
                                "wf/artifact_contracts.json",
                                "wf/workflow.lgwf",
                                "wf/01_collect_context/workflow.lgwf",
                                "wf/01_collect_context/artifact_contracts.json",
                                "wf/01_collect_context/agents/prompt.md",
                                "wf/01_collect_context/scripts/run.py",
                                "wf/01_collect_context/resources/README.md",
                                "tests/README.md",
                                "tests/test_workflow_structure.py",
                            ],
                            "target_dirs": [
                                "scripts",
                                "tests",
                                "ws",
                                "wf",
                                "wf/shared",
                                "wf/shared/scripts",
                                "wf/01_collect_context",
                                "wf/01_collect_context/agents",
                                "wf/01_collect_context/scripts",
                                "wf/01_collect_context/resources",
                            ],
                        },
                        {
                            "step_slug": "run_checks",
                            "step_name": "运行检查",
                            "stage_id": "run_checks",
                            "goal": "运行目标检查。",
                            "inputs": [".lgwf/collect_context_result.json"],
                            "outputs": [".lgwf/run_checks_result.json"],
                            "dependencies": ["collect_context"],
                            "implementation_suggestions": ["生成检查阶段 workflow 和私有资源。"],
                            "acceptance_notes": ["检查阶段目录自包含。"],
                            "out_of_scope": ["自动修复"],
                            "confirmation_points": ["依赖关系正确"],
                            "target_files": [
                                "wf/02_run_checks/workflow.lgwf",
                                "wf/02_run_checks/artifact_contracts.json",
                                "wf/02_run_checks/agents/prompt.md",
                                "wf/02_run_checks/scripts/run.py",
                                "wf/02_run_checks/resources/README.md",
                            ],
                            "target_dirs": [
                                "wf/02_run_checks",
                                "wf/02_run_checks/agents",
                                "wf/02_run_checks/scripts",
                                "wf/02_run_checks/resources",
                            ],
                        },
                    ],
                    "file_designs": [
                        {"path": path, "owner_step": "collect_context"}
                        for path in [
                            "AGENTS.md",
                            "README.md",
                            "entry_contract.json",
                            "wf/artifact_contracts.json",
                            "wf/workflow.lgwf",
                            "wf/01_collect_context/workflow.lgwf",
                            "wf/01_collect_context/artifact_contracts.json",
                            "wf/01_collect_context/agents/prompt.md",
                            "wf/01_collect_context/scripts/run.py",
                            "wf/01_collect_context/resources/README.md",
                            "wf/02_run_checks/workflow.lgwf",
                            "wf/02_run_checks/artifact_contracts.json",
                            "wf/02_run_checks/agents/prompt.md",
                            "wf/02_run_checks/scripts/run.py",
                            "wf/02_run_checks/resources/README.md",
                            "tests/README.md",
                            "tests/test_workflow_structure.py",
                        ]
                    ],
                    "directory_designs": [
                        {"path": path, "owner_step": "collect_context"}
                        for path in [
                            "scripts",
                            "tests",
                            "ws",
                            "wf",
                            "wf/shared",
                            "wf/shared/scripts",
                            "wf/01_collect_context",
                            "wf/01_collect_context/agents",
                            "wf/01_collect_context/scripts",
                            "wf/01_collect_context/resources",
                            "wf/02_run_checks",
                            "wf/02_run_checks/agents",
                            "wf/02_run_checks/scripts",
                            "wf/02_run_checks/resources",
                        ]
                    ],
                }
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
            for unit in units:
                self.assertNotIn("implementation_reason", unit)
                self.assertNotIn("observe", unit)
                self.assertNotIn("repair_focus", unit)
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
                ["wf/workflow.lgwf"],
            )
            self.assertEqual(root_unit["package_relative_dirs"], ["wf"])
            self.assertEqual(stage_unit["stage_id"], "collect_context")
            self.assertEqual(stage_unit["stage_dir"], "01_collect_context")
            self.assertEqual(stage_unit["workflow_ref"], "wf/01_collect_context/workflow.lgwf")
            self.assertIn("wf/01_collect_context/scripts/run.py", stage_unit["planned_files"])
            self.assertIn("wf/01_collect_context/artifact_contracts.json", stage_unit["planned_files"])
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

    def test_prepare_units_includes_confirmed_file_design_paths_from_step_designs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            lgwf_dir = root / ".lgwf"
            step_designs = json.loads((lgwf_dir / "step_designs.json").read_text(encoding="utf-8"))
            confirmed = step_designs["confirmed"]
            confirmed["step_designs"][0]["target_files"] = [
                "wf/01_collect_context/scripts/prepare_context.py"
            ]
            confirmed["step_designs"][0]["target_dirs"] = ["wf/01_collect_context/scripts"]
            confirmed["file_designs"] = [
                {
                    "path": "wf/01_collect_context/scripts/prepare_context.py",
                    "kind": "python_script",
                    "owner_step": "collect_context",
                    "purpose": "准备上下文",
                }
            ]
            confirmed["directory_designs"] = [
                {
                    "path": "wf/01_collect_context/scripts",
                    "purpose": "阶段脚本目录",
                    "owner_step": "collect_context",
                }
            ]
            write_json(lgwf_dir / "step_designs.json", step_designs)

            result = self.prepare_units.build_implementation_units(root)
            stage_unit = next(unit for unit in result["implementation_units"] if unit["unit_id"] == "stage_01_collect_context")

            self.assertIn("wf/01_collect_context/scripts/prepare_context.py", stage_unit["output_files"])
            self.assertIn("wf/01_collect_context/scripts", stage_unit["output_dirs"])
            self.assertEqual(stage_unit["file_designs"][0]["owner_step"], "collect_context")
            self.assertEqual(stage_unit["directory_designs"][0]["owner_step"], "collect_context")

    def test_prepare_current_injects_package_json_output_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            units = self.prepare_units.build_implementation_units(root)["implementation_units"]
            package_unit = next(unit for unit in units if unit["unit_id"] == "package_contracts")

            context = self.prepare_current.build_current_implementation_unit_context(root, package_unit)
            target_schemas = context["target_output_file_schemas"]
            result_schema = context["codex_output_json_schema"]
            instructions = "\n".join(context["instructions"])

            self.assertIn("entry_contract.json", target_schemas)
            self.assertIn("wf/artifact_contracts.json", target_schemas)
            self.assertIn("input_schema", target_schemas["entry_contract.json"]["required"])
            self.assertIn("delivery_artifacts", target_schemas["wf/artifact_contracts.json"]["required"])
            self.assertTrue(context["artifact_contract_guidance"]["required"])
            self.assertIn("root_artifact_contract", context["artifact_contract_guidance"])
            self.assertIn("unit_id", result_schema["required"])
            self.assertIn("generated_files", result_schema["required"])
            self.assertNotIn("implementation_reference_context", context)
            self.assertIn("缺少 schema 时记录 blocked_reason", instructions)
            self.assertIn("content_mode=exact", instructions)
            self.assertIn("LGWF_PLACEHOLDER", instructions)
            self.assertIn("不要递归搜索 .lgwf", instructions)
            self.assertNotIn("resources/lgwf_dsl_authoring.md", instructions)
            self.assertIn("exact_content", instructions)
            self.assertIn("不生成、不筛选、不摘录 LGWF DSL schema", instructions)

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

    def test_merge_keeps_ok_unit_risks_as_caveats_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            result = self.merge_units.merge_implementation_results(
                root,
                {
                    "unit_results": [
                        {
                            "unit_id": "package_contracts",
                            "status": "ok",
                            "generated_files": [{"path": "AGENTS.md"}],
                            "remaining_risks": ["later units must publish stage files"],
                        }
                    ]
                },
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["remaining_risks"], [])
            self.assertEqual(
                result["unit_caveats"],
                [
                    {
                        "unit_id": "package_contracts",
                        "status": "ok",
                        "remaining_risks": ["later units must publish stage files"],
                        "blocking": False,
                    }
                ],
            )

    def test_merge_promotes_non_ok_unit_risks_to_remaining_risks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            result = self.merge_units.merge_implementation_results(
                root,
                {
                    "unit_results": [
                        {
                            "unit_id": "stage_02_run_checks",
                            "status": "partial",
                            "generated_files": [{"path": "wf/02_run_checks/workflow.lgwf"}],
                            "remaining_risks": ["script missing validation branch"],
                        }
                    ]
                },
            )

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["remaining_risks"], ["script missing validation branch"])
            self.assertEqual(result["unit_caveats"][0]["blocking"], True)

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
            self.assertEqual(result["unit_id"], "stage_01_collect_context")
            self.assertIn("step_designs", result)
            self.assertIn("file_designs", result)
            self.assertIn("directory_designs", result)
            self.assertNotIn("target_package_abs", result)
            self.assertNotIn("target_package_abs", result["current_implementation_unit"])
            self.assertNotIn("workspace_root", result["current_implementation_unit"])
            self.assertEqual(result["output_files"], unit["output_files"])
            self.assertNotIn("implementation_reference_context", result)
            self.assertEqual(result["unit_output_dir"], ".lgwf/implementation_stage/stage_01_collect_context")
            self.assertFalse((target_package / "wf" / "01_collect_context" / "workflow.lgwf").is_file())
            self.assertTrue((root / ".lgwf" / "implementation_stage" / "stage_01_collect_context").is_dir())
            self.assertTrue((root / ".lgwf" / "current_implementation_unit_context.json").is_file())
            self.assertNotIn("lgwf_dsl_contract", result)
            self.assertNotIn("resources/lgwf_dsl_authoring.md", "\n".join(result["instructions"]))
            self.assertIn("exact_content", "\n".join(result["instructions"]))
            script_source = (
                IMPLEMENT_ROOT
                / "01_implement_units/01_implement_one_unit/scripts/prepare_current_implementation_unit.py"
            ).read_text(encoding="utf-8")
            self.assertNotIn("def lgwf_dsl_contract", script_source)

    def test_prepare_current_unit_injects_stage_artifact_contract_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            units = self.prepare_units.build_implementation_units(root)["implementation_units"]
            stage_unit = next(unit for unit in units if unit["unit_id"] == "stage_01_collect_context")
            stage_unit["target_package_abs"] = str(target_package.resolve())

            context = self.prepare_current.build_current_implementation_unit_context(root, stage_unit)

            target_schemas = context["target_output_file_schemas"]
            guidance = context["artifact_contract_guidance"]
            self.assertIn("wf/01_collect_context/artifact_contracts.json", target_schemas)
            self.assertIn("bootstrap_inputs", target_schemas["wf/01_collect_context/artifact_contracts.json"]["required"])
            self.assertTrue(guidance["required"])
            self.assertIn("wf/01_collect_context/artifact_contracts.json", guidance["stage_artifact_contracts"])
            stage_guidance = guidance["stage_artifact_contracts"]["wf/01_collect_context/artifact_contracts.json"]
            self.assertEqual(stage_guidance["bootstrap_inputs"], [".lgwf/create_requirements.json"])
            self.assertEqual(stage_guidance["final_outputs"], [".lgwf/collect_context_result.json"])
            self.assertEqual(stage_guidance["audit_scope"], "lgwf.py audit wf/01_collect_context/workflow.lgwf")

    def test_prepare_current_unit_keeps_root_design_context_without_dynamic_dsl_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            units = self.prepare_units.build_implementation_units(root)["implementation_units"]
            root_unit = next(unit for unit in units if unit["unit_id"] == "root_workflow")
            root_unit["target_package_abs"] = str(target_package.resolve())

            context = self.prepare_current.build_current_implementation_unit_context(root, root_unit)

            self.assertNotIn("lgwf_dsl_contract", context)
            guidance = context["artifact_contract_guidance"]
            self.assertFalse(guidance["required"])
            self.assertIn("不生成 artifact_contracts.json", guidance["reason"])
            by_stage = {item.get("stage_id"): item for item in context["step_designs"]}
            self.assertIn("wf/01_collect_context/workflow.lgwf", by_stage["collect_context"]["target_files"])
            self.assertEqual(by_stage["collect_context"]["inputs"], [".lgwf/create_requirements.json"])
            self.assertEqual(by_stage["collect_context"]["outputs"], [".lgwf/collect_context_result.json"])
            self.assertIn("wf/02_run_checks/workflow.lgwf", by_stage["run_checks"]["target_files"])
            self.assertEqual(by_stage["run_checks"]["inputs"], [".lgwf/collect_context_result.json"])
            self.assertEqual(by_stage["run_checks"]["outputs"], [".lgwf/run_checks_result.json"])
            instructions = "\n".join(context["instructions"])
            self.assertNotIn("lgwf_dsl_contract", instructions)
            self.assertNotIn("resources/lgwf_dsl_authoring.md", instructions)
            self.assertIn("exact_content", instructions)
            self.assertIn("artifact_contract_guidance", instructions)

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

    def test_publish_current_unit_accepts_generated_files_with_unit_stage_prefix(self) -> None:
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
                    "generated_files": [
                        ".lgwf/implementation_stage/stage_01_collect_context/wf/01_collect_context/workflow.lgwf"
                    ],
                },
            )

            result = self.publish_current.publish_current_implementation_unit_result(root)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["generated_files"], [{"path": "wf/01_collect_context/workflow.lgwf"}])
            self.assertTrue((target_package / "wf" / "01_collect_context" / "workflow.lgwf").is_file())

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

    def test_publish_repair_result_updates_target_and_implementation_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target_package = self.seed_context(root)
            (target_package / "wf").mkdir(parents=True, exist_ok=True)
            write_json(
                root / ".lgwf" / "implementation_repair_reason.json",
                {
                    "repair_required": True,
                    "unit_output_dir": ".lgwf/implementation_repair_stage",
                    "target_files": ["wf/workflow.lgwf"],
                },
            )
            write_json(
                root / ".lgwf" / "implementation_repair_result.json",
                {"status": "ok", "generated_files": [{"path": "wf/workflow.lgwf"}]},
            )
            write_json(
                root / ".lgwf" / "implementation_result.json",
                {"status": "ok", "generated_files": [{"path": "README.md"}]},
            )
            staged = root / ".lgwf" / "implementation_repair_stage" / "wf" / "workflow.lgwf"
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_text("WORKFLOW demo;\n", encoding="utf-8")

            result = self.publish_repair.publish_repair_result(root)

            self.assertEqual(result["status"], "ok")
            self.assertEqual((target_package / "wf" / "workflow.lgwf").read_text(encoding="utf-8"), "WORKFLOW demo;\n")
            implementation_result = json.loads(
                (root / ".lgwf" / "implementation_result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                implementation_result["generated_files"],
                [{"path": "README.md"}, {"path": "wf/workflow.lgwf"}],
            )
            self.assertEqual(implementation_result["repair_rounds"][0]["status"], "ok")

    def test_publish_repair_result_records_invalid_plan_for_files_outside_reason_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            write_json(
                root / ".lgwf" / "implementation_repair_reason.json",
                {
                    "repair_required": True,
                    "unit_output_dir": ".lgwf/implementation_repair_stage",
                    "target_files": ["wf/workflow.lgwf"],
                },
            )
            write_json(
                root / ".lgwf" / "implementation_repair_result.json",
                {"status": "ok", "generated_files": [{"path": "README.md"}]},
            )
            write_json(root / ".lgwf" / "implementation_result.json", {"status": "ok", "generated_files": []})

            result = self.publish_repair.publish_repair_result(root)

            self.assertEqual(result["status"], "invalid_plan")
            implementation_result = json.loads(
                (root / ".lgwf" / "implementation_result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(implementation_result["repair_rounds"][0]["status"], "invalid_plan")
            self.assertTrue(any("outside target_files" in item for item in result["failures"]))

    def test_publish_repair_result_records_blocked_without_staging_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.seed_context(root)
            write_json(
                root / ".lgwf" / "implementation_repair_reason.json",
                {
                    "repair_required": True,
                    "blocked": True,
                    "unit_output_dir": ".lgwf/implementation_repair_stage",
                    "target_files": [],
                },
            )
            write_json(
                root / ".lgwf" / "implementation_repair_result.json",
                {"status": "blocked", "remaining_risks": ["audit runner missing"]},
            )
            write_json(root / ".lgwf" / "implementation_result.json", {"status": "ok", "generated_files": []})

            result = self.publish_repair.publish_repair_result(root)

            self.assertEqual(result["status"], "blocked")
            self.assertFalse((root / ".lgwf" / "implementation_repair_stage").exists())
            implementation_result = json.loads(
                (root / ".lgwf" / "implementation_result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(implementation_result["repair_rounds"][0]["status"], "blocked")
            self.assertEqual(implementation_result["repair_rounds"][0]["remaining_risks"], ["audit runner missing"])


if __name__ == "__main__":
    unittest.main()
