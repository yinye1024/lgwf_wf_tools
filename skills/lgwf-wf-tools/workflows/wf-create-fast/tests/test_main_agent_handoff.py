from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import lgwf.handoff as handoff_module


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PACKAGE_ROOT / "wf" / "04_main_agent_handoff" / "scripts" / "prepare_main_agent_handoff.py"


def load_handoff_module():
    spec = importlib.util.spec_from_file_location("wf_create_fast_prepare_main_agent_handoff", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MainAgentHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_handoff_module()

    def write_required_artifacts(self, lgwf_dir: Path, target_abs: Path) -> None:
        (lgwf_dir / "create_requirements.json").write_text(
            json.dumps(
                {
                    "confirmed": {
                        "workflow_name": "example-workflow",
                        "target_package_root": "skills/example-workflow",
                        "package_profile": "internal_workflow_package",
                        "purpose": "创建示例 LGWF workflow",
                        "expected_outputs": ["生成结构化报告"],
                        "non_goals": ["不运行下游 post-fix"],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (lgwf_dir / "business_flow.json").write_text(
            json.dumps(
                {
                    "confirmed": {
                        "workflow_name": "example-workflow",
                        "business_goal": "生成并校验报告",
                        "stages": [
                            {
                                "stage_id": "prepare",
                                "stage_dir": "01_prepare",
                                "key_nodes": ["prepare_input"],
                            }
                        ],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (lgwf_dir / "scaffold_package_result.json").write_text(
            json.dumps(
                {
                    "scaffold_plan": {
                        "workflow_name": "example-workflow",
                        "target_package_root": "skills/example-workflow",
                        "package_profile": "internal_workflow_package",
                        "stage_manifest": [
                            {
                                "stage_id": "prepare",
                                "stage_dir": "01_prepare",
                                "workflow_ref": "wf/01_prepare/workflow.lgwf",
                            }
                        ],
                        "create_dirs": ["wf", "wf/01_prepare", "tests"],
                        "create_files": ["AGENTS.md", "wf/workflow.lgwf", "tests/test_structure.py"],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (lgwf_dir / "materialize_scaffold_result.json").write_text(
            json.dumps(
                {
                    "status": "ok",
                    "workflow_name": "example-workflow",
                    "target_package_root": "skills/example-workflow",
                    "target_package_abs": str(target_abs),
                    "created_files": ["AGENTS.md", "wf/workflow.lgwf", "tests/test_structure.py"],
                    "skipped_existing_files": [],
                    "validation_commands": [
                        f'python skills/lgwf-wf-tools/vendor/lgwf-client-assist/scripts/lgwf.py audit "{target_abs / "wf" / "workflow.lgwf"}"',
                        f'python -m unittest discover "{target_abs / "tests"}"',
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def test_writes_handoff_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            target_abs = Path(tmp) / "target with spaces" / "example-workflow"
            (target_abs / "wf").mkdir(parents=True)
            (target_abs / "wf" / "workflow.lgwf").write_text("WORKFLOW example;\n", encoding="utf-8")
            lgwf_dir = work_dir / ".lgwf"
            lgwf_dir.mkdir()
            self.write_required_artifacts(lgwf_dir, target_abs)

            payload = self.module.prepare_main_agent_handoff(work_dir)

            self.assertEqual(payload["handoff_schema_version"], 5)
            self.assertEqual(payload["workflow_id"], "wf-create-fast")
            self.assertEqual(payload["next_action"], "main_agent_authoring")
            self.assertEqual(payload["agent_instruction"], "handle_main_agent_authoring")
            self.assertEqual(payload["handoff_mode"], "confirmed_artifacts_and_target_package")
            self.assertEqual(payload["execution_mode"], "plan_then_execute")
            self.assertEqual(
                payload["required_context"],
                ["confirmed_requirements", "confirmed_business_flow", "target_package", "execution_contract"],
            )
            self.assertEqual(payload["handoff_status"], "ready_for_main_agent")
            self.assertTrue(payload["handoff_ack_required"])
            self.assertEqual(payload["confirmed_requirements"], ".lgwf/create_requirements.json")
            self.assertEqual(payload["confirmed_business_flow"], ".lgwf/business_flow.json")
            self.assertEqual(payload["target_package"]["validation_commands"][0].count('"'), 2)
            self.assertEqual(payload["target_package"]["validation_commands"][1].count('"'), 2)
            self.assertEqual(payload["target_package"]["root_abs"], str(target_abs))
            self.assertEqual(payload["target_package"]["workflow_lgwf"], str(target_abs / "wf" / "workflow.lgwf"))
            self.assertEqual(payload["target_package"]["work_dir"], str(target_abs / "ws"))
            self.assertEqual(payload["target_package"]["edit_dirs"], [str(target_abs)])
            self.assertEqual(
                payload["target_package"]["materialization"],
                {
                    "status": "ok",
                    "created_file_count": 3,
                    "created_files": ["AGENTS.md", "wf/workflow.lgwf", "tests/test_structure.py"],
                    "skipped_existing_file_count": 0,
                    "skipped_existing_files": [],
                },
            )
            execution_contract = payload["execution_contract"]
            self.assertTrue(execution_contract["plan_required_before_target_edits"])
            self.assertEqual(execution_contract["plan_mechanism"], "main_agent_plan_capability")
            self.assertLess(
                execution_contract["execution_order"].index("create_execution_plan"),
                execution_contract["execution_order"].index("execute_plan_and_track_progress"),
            )
            self.assertEqual(
                execution_contract["minimum_plan_steps"],
                [
                    "inspect_confirmed_context_and_scaffold",
                    "implement_target_package",
                    "run_validation_commands",
                ],
            )
            self.assertNotIn("target_package_root", payload)
            self.assertNotIn("target_package_abs", payload)
            self.assertNotIn("target_workflow_lgwf", payload)
            self.assertNotIn("edit_dirs", payload)
            self.assertNotIn("self_contained", payload)
            self.assertNotIn("source_artifacts", payload)
            self.assertNotIn("source_artifacts_embedded", payload)
            self.assertNotIn("scaffold_plan", payload)
            self.assertNotIn("materialize_result", payload)
            self.assertNotIn("implementation_context", payload)
            self.assertNotIn("implementation_checklist", payload)
            self.assertNotIn("guardrails", payload)
            self.assertNotIn("validation_commands", payload)
            self.assertFalse(payload["requires_user_confirmation"])
            self.assertFalse(payload["auto_execute_downstream_workflow"])
            written = json.loads((lgwf_dir / "main_agent_authoring_handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(written, payload)

    def test_main_agent_authoring_handoff_can_be_acknowledged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            target_abs = Path(tmp) / "target"
            lgwf_dir = work_dir / ".lgwf"
            lgwf_dir.mkdir()
            self.write_required_artifacts(lgwf_dir, target_abs)

            payload = self.module.prepare_main_agent_handoff(work_dir)
            pending = handoff_module.create_pending_action(
                work_dir,
                {
                    "type": "agent_handoff",
                    "next_action": payload["next_action"],
                    "workflow_id": payload["workflow_id"],
                    "requires_user_confirmation": payload["requires_user_confirmation"],
                    "auto_execute": False,
                    "agent_instruction": payload["agent_instruction"],
                    "payload": payload,
                },
                request_id="handoff-main-agent",
            )
            ack = handoff_module.acknowledge_pending_action(
                work_dir,
                pending["request_id"],
                comment="main agent received",
            )

            self.assertEqual(ack["status"], "received")
            self.assertFalse((work_dir / ".lgwf" / "handoff" / "handoff-main-agent.pending.json").exists())
            self.assertTrue((work_dir / ".lgwf" / "handoff" / "handoff-main-agent.received.json").is_file())

    def test_requires_internal_artifacts_to_build_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            (work_dir / ".lgwf").mkdir()

            with self.assertRaisesRegex(ValueError, "create_requirements.json"):
                self.module.prepare_main_agent_handoff(work_dir)

    def test_handoff_prompt_forbids_standard_back_half(self) -> None:
        prompt = (PACKAGE_ROOT / "wf" / "04_main_agent_handoff" / "handoff_main_agent_authoring.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("step_designs.json", prompt)
        self.assertIn("03_confirm_step_designs", prompt)
        self.assertIn("04_implement_steps_react", prompt)
        self.assertIn("不自动启动其他下游 workflow", prompt)

    def test_handoff_prompt_requires_plan_before_target_edits(self) -> None:
        prompt = (PACKAGE_ROOT / "wf" / "04_main_agent_handoff" / "handoff_main_agent_authoring.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("在首次修改目标 package 前", prompt)
        self.assertIn("使用主 agent 的计划能力生成可见执行计划", prompt)
        self.assertIn("按计划逐项实施并持续更新计划状态", prompt)
        self.assertIn("不得跳过计划直接编辑目标 package", prompt)

    def test_stage_publishes_runtime_handoff_after_writing_artifact(self) -> None:
        workflow = (PACKAGE_ROOT / "wf" / "04_main_agent_handoff" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("PY prepare_main_agent_handoff", workflow)
        self.assertIn('WRITE workspace file ".lgwf/main_agent_authoring_handoff.json"', workflow)
        self.assertIn("HANDOFF handoff_main_agent_authoring", workflow)
        self.assertIn("CONTEXT state.lgwf_wf_create_fast.main_agent_handoff_payload", workflow)
        self.assertIn("RESULT state.lgwf_wf_create_fast.main_agent_handoff", workflow)
        self.assertIn("THEN handoff_main_agent_authoring;", workflow)


if __name__ == "__main__":
    unittest.main()
