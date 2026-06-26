from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from test_lgwf_wf_create_scaffold_contract import WorkflowCreateScaffoldContractTest  # noqa: F401


ROOT = Path(__file__).resolve().parents[1]


def load_module(relative: str, name: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class pushd:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous = Path.cwd()

    def __enter__(self) -> None:
        os.chdir(self.path)

    def __exit__(self, exc_type, exc, tb) -> None:
        os.chdir(self.previous)


class StructuredContractsTest(unittest.TestCase):
    def test_human_facing_test_and_prompt_text_has_no_mojibake(self) -> None:
        checked_files = (
            "tests/test_lgwf_plan_workflow_runtime_e2e.py",
            "01_generate_plan/02_generate_plan_proposal/agents/reason.md",
            "02_generate_acceptance/00_generate_acceptance_proposal/agents/reason.md",
            "02_generate_acceptance/00_generate_acceptance_proposal/agents/act.md",
            "02_generate_acceptance/00_generate_acceptance_proposal/agents/spec.md",
        )
        mojibake_fragments = (
            "鍚",
            "浠",
            "鐨",
            "璁",
            "楠",
            "骞",
            "瑕",
            "涓",
            "鎴",
            "�",
            "€",
        )
        for relative in checked_files:
            text = (ROOT / relative).read_text(encoding="utf-8")
            for fragment in mojibake_fragments:
                self.assertNotIn(fragment, text, f"{relative} contains mojibake fragment {fragment!r}")

    def test_init_plan_preserves_structured_fields(self) -> None:
        manager = load_module("04_execute_react_loop/00_prepare/scripts/manage_react_task.py", "manager")
        with tempfile.TemporaryDirectory() as temp:
            plan = {
                "tasks": [
                    {
                        "task_id": "task-1",
                        "title": "Title",
                        "scope_detail": {"files": ["a.py"]},
                        "implementation_steps": [{"step": "change"}],
                        "acceptance_seed": ["seed"],
                        "required_checks_hint": ["python -m unittest"],
                    }
                ]
            }
            stored = manager.init_plan(Path(temp), plan)
            task = stored["tasks"][0]
            self.assertEqual(task["scope_detail"], {"files": ["a.py"]})
            self.assertEqual(task["implementation_steps"], [{"step": "change"}])
            self.assertEqual(task["status"], "planned")

    def test_set_acceptance_requires_plan_validation_map_coverage(self) -> None:
        manager = load_module("04_execute_react_loop/00_prepare/scripts/manage_react_task.py", "manager2")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager.init_plan(root, {"tasks": [{"task_id": "task-1", "implementation_steps": ["a", "b"]}]})
            acceptance = {
                "tasks": [
                    {
                        "task_id": "task-1",
                        "criteria": ["done"],
                        "required_checks": ["test"],
                        "review_focus": ["scope"],
                        "out_of_scope": ["unrelated files"],
                        "plan_validation_map": [
                            {"plan_step_index": 0, "plan_step": "a", "expected_evidence": "x", "validation": "check"},
                            {"plan_step_index": 1, "plan_step": "b", "expected_evidence": "y", "validation": "check"},
                        ],
                    }
                ]
            }
            manager.set_acceptance(root, acceptance)
            stored = json.loads((root / ".lgwf" / "react_acceptance_plan.json").read_text(encoding="utf-8"))
            indexes = [item["plan_step_index"] for item in stored["tasks"][0]["plan_validation_map"]]
            self.assertEqual(indexes, [0, 1])

    def test_set_acceptance_rejects_missing_plan_validation_map_coverage(self) -> None:
        manager = load_module("04_execute_react_loop/00_prepare/scripts/manage_react_task.py", "manager3")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manager.init_plan(root, {"tasks": [{"task_id": "task-1", "implementation_steps": ["a", "b"]}]})
            acceptance = {
                "tasks": [
                    {
                        "task_id": "task-1",
                        "criteria": ["done"],
                        "required_checks": ["test"],
                        "review_focus": ["scope"],
                        "out_of_scope": ["unrelated files"],
                        "plan_validation_map": [
                            {"plan_step_index": 0, "plan_step": "a", "expected_evidence": "x", "validation": "check"}
                        ],
                    }
                ]
            }
            with self.assertRaisesRegex(ValueError, "cover implementation_steps"):
                manager.set_acceptance(root, acceptance)

    def test_record_review_rejects_pass_without_evidence_details(self) -> None:
        record = load_module("04_execute_react_loop/02_record/scripts/record_react_task_review.py", "record")
        with self.assertRaises(SystemExit):
            record.validate_result({"verdict": "pass", "pass": True, "accepted": True, "required_follow_up": []})

    def test_record_review_accepts_structured_pass_details(self) -> None:
        record = load_module("04_execute_react_loop/02_record/scripts/record_react_task_review.py", "record2")
        record.validate_result(
            {
                "verdict": "pass",
                "pass": True,
                "accepted": True,
                "evidence": ["tests passed"],
                "criteria_results": [{"criteria": "done", "passed": True}],
                "required_check_results": [{"check": "unit", "passed": True}],
                "negative_check_results": [{"check": "no out of scope", "passed": True}],
                "risk_check_results": [{"risk": "scope drift", "passed": True}],
                "plan_validation_results": [{"plan_step_index": 0, "passed": True}],
                "scope_compliance": {"within_scope": True, "issues": []},
                "required_follow_up": [],
            }
        )

    def test_decide_scripts_emit_top_level_next(self) -> None:
        for relative, observe_name, proposal_name in (
            ("01_generate_plan/02_generate_plan_proposal/scripts/decide.py", "react_task_plan_observe.json", "react_task_plan_proposal.json"),
            ("02_generate_acceptance/00_generate_acceptance_proposal/scripts/decide.py", "react_acceptance_observe.json", "react_acceptance_proposal.json"),
            ("04_execute_react_loop/01_implement_task/scripts/decide.py", "react_task_result.json", None),
        ):
            self.assertTrue((ROOT / relative).exists())
            self.assertIn("next", (ROOT / relative).read_text(encoding="utf-8"))

    def test_acceptance_decide_accepts_utf8_bom_json(self) -> None:
        decide = load_module("02_generate_acceptance/00_generate_acceptance_proposal/scripts/decide.py", "acceptance_decide_bom")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            lgwf_dir.mkdir()
            (lgwf_dir / "react_acceptance_proposal.json").write_text(
                json.dumps({"tasks": [{"task_id": "task-1"}]}),
                encoding="utf-8",
            )
            (lgwf_dir / "react_acceptance_observe.json").write_text(
                json.dumps(
                    {
                        "verdict": "pass",
                        "acceptance_is_executable": True,
                        "plan_validation_map_complete": True,
                        "ready_for_confirmation": True,
                        "issues": [],
                        "required_changes": [],
                    }
                ),
                encoding="utf-8-sig",
            )
            output = io.StringIO()
            with pushd(root), redirect_stdout(output):
                decide.main()
            self.assertEqual(json.loads(output.getvalue())["next"], "exit")

    def test_confirmation_template_mentions_structured_fields(self) -> None:
        template = (ROOT / "03_confirm_plan_and_acceptance/00_user_decision_template/plan_acceptance_decision_template.md").read_text(encoding="utf-8")
        for text in (
            "当前建议",
            "建议 approve",
            "建议 reject",
            "建议 revise",
            "质量风险",
            "不得把完整 `confirmation_context`",
            "不直接读取或要求读取其他 proposal 文件",
            "ROUTE_ON_DECISION",
            "mojibake",
            "summary.problem_statement",
            "summary.proposed_approach",
            "summary.key_decisions",
            "scope_detail",
            "implementation_steps",
            "criteria_details",
            "required_checks_details",
            "traceability",
            "plan_validation_map",
        ):
            self.assertIn(text, template)

    def test_contract_confirmation_uses_decision_route(self) -> None:
        workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("APPROVAL confirm_plan_and_acceptance", workflow)
        self.assertIn("ROUTE_ON_DECISION", workflow)
        self.assertIn("ROUTE confirm_plan_and_acceptance", workflow)
        self.assertIn('WHEN "approve" THEN apply_confirmed_contracts', workflow)
        self.assertIn('WHEN "revise" THEN finish_contract_review', workflow)
        self.assertIn('WHEN "reject" THEN finish_contract_review', workflow)
        self.assertNotIn("route_contract_decision", workflow)

    def test_all_lgwf_plan_approval_nodes_use_business_decision_routes(self) -> None:
        root_workflow = (ROOT / "workflow.lgwf").read_text(encoding="utf-8")
        generate_workflow = (ROOT / "01_generate_plan/workflow.lgwf").read_text(encoding="utf-8")
        execute_workflow = (ROOT / "04_execute_react_loop/workflow.lgwf").read_text(encoding="utf-8")

        self.assertIn("APPROVAL confirm_plan_and_acceptance", root_workflow)
        self.assertIn("ROUTE_ON_DECISION", root_workflow)
        self.assertIn('WHEN "reject" THEN finish_contract_review', root_workflow)

        self.assertIn("APPROVAL collect_react_task_request", generate_workflow)
        self.assertIn("ROUTE_ON_DECISION", generate_workflow)
        self.assertIn("ROUTE collect_react_task_request", generate_workflow)
        self.assertIn('WHEN "approve" THEN validate_plan_analysis_targets', generate_workflow)
        self.assertIn('WHEN "reject" THEN finish_react_task_request', generate_workflow)

        self.assertIn("APPROVAL decide_react_task_block", execute_workflow)
        self.assertIn("ROUTE_ON_DECISION", execute_workflow)
        self.assertIn("ROUTE decide_react_task_block", execute_workflow)
        self.assertIn('WHEN "approve" THEN resolve_max_attempt_decision', execute_workflow)
        self.assertIn('WHEN "reject" THEN resolve_max_attempt_decision', execute_workflow)

    def test_confirmation_context_includes_summary(self) -> None:
        route = load_module("02_generate_acceptance/01_route_acceptance_generation/scripts/route_acceptance_generation.py", "route_acceptance")
        plan = {
            "tasks": [
                {
                    "task_id": "task-1",
                    "title": "Task 1",
                    "implementation_steps": ["step"],
                }
            ]
        }
        acceptance = {
            "tasks": [
                {
                    "task_id": "task-1",
                    "required_checks": ["check"],
                }
            ]
        }
        confirmation = route.format_confirmation(plan, acceptance)
        self.assertIn("summary", confirmation)
        self.assertIn("problem_statement", confirmation["summary"])
        self.assertEqual(confirmation["summary"]["workflow_flow"], ["Task 1"])

    def test_react_codex_slots_receive_analysis_targets(self) -> None:
        for relative in (
            "01_generate_plan/workflow.lgwf",
            "02_generate_acceptance/workflow.lgwf",
            "04_execute_react_loop/workflow.lgwf",
        ):
            workflow = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("TARGET_DIRS state.lgwf_plan.plan_target_validation.analysis_target_dirs", workflow)
            self.assertIn("TARGET_FILES state.lgwf_plan.plan_target_validation.analysis_target_files", workflow)

    def test_codex_json_artifacts_use_output_json(self) -> None:
        contracts = (
            (
                "01_generate_plan/workflow.lgwf",
                "01_generate_plan/02_generate_plan_proposal/agents/act.md",
                ".lgwf/react_task_plan_proposal.json",
                True,
            ),
            (
                "01_generate_plan/workflow.lgwf",
                "01_generate_plan/02_generate_plan_proposal/agents/observe.md",
                ".lgwf/react_task_plan_observe.json",
                False,
            ),
            (
                "02_generate_acceptance/workflow.lgwf",
                "02_generate_acceptance/00_generate_acceptance_proposal/agents/reason.md",
                ".lgwf/react_acceptance_reason.json",
                True,
            ),
            (
                "02_generate_acceptance/workflow.lgwf",
                "02_generate_acceptance/00_generate_acceptance_proposal/agents/act.md",
                ".lgwf/react_acceptance_proposal.json",
                True,
            ),
            (
                "02_generate_acceptance/workflow.lgwf",
                "02_generate_acceptance/00_generate_acceptance_proposal/agents/observe.md",
                ".lgwf/react_acceptance_observe.json",
                False,
            ),
            (
                "04_execute_react_loop/workflow.lgwf",
                "04_execute_react_loop/01_implement_task/agents/act.md",
                ".lgwf/react_task_input.json",
                False,
            ),
            (
                "04_execute_react_loop/workflow.lgwf",
                "04_execute_react_loop/01_implement_task/agents/observe.md",
                ".lgwf/react_task_result.json",
                False,
            ),
        )
        for workflow_relative, prompt_relative, artifact, uses_as_file in contracts:
            workflow = (ROOT / workflow_relative).read_text(encoding="utf-8")
            prompt = (ROOT / prompt_relative).read_text(encoding="utf-8")
            self.assertIn(f'OUTPUT_JSON "{artifact}"', workflow)
            if uses_as_file:
                self.assertIn(f'OUTPUT_JSON "{artifact}" AS_FILE', workflow)
            self.assertIn("OUTPUT_JSON", prompt)
            self.assertIn(artifact, prompt)

    def test_large_codex_json_artifacts_use_as_file(self) -> None:
        expectations = (
            ("01_generate_plan/workflow.lgwf", ".lgwf/react_task_plan_proposal.json"),
            ("02_generate_acceptance/workflow.lgwf", ".lgwf/react_acceptance_reason.json"),
            ("02_generate_acceptance/workflow.lgwf", ".lgwf/react_acceptance_proposal.json"),
        )
        for workflow_relative, artifact in expectations:
            workflow = (ROOT / workflow_relative).read_text(encoding="utf-8")
            self.assertIn(f'OUTPUT_JSON "{artifact}" AS_FILE', workflow)

    def test_execute_loop_routes_back_to_next_task(self) -> None:
        workflow = (ROOT / "04_execute_react_loop/workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn("ROUTE route_react_task_review", workflow)
        self.assertIn('WHEN "move_next_task" THEN prepare_react_task_review', workflow)
        self.assertIn('WHEN "continue_repair" THEN prepare_react_task_review', workflow)
        self.assertIn('WHEN "requires_user_approval" THEN decide_react_task_block', workflow)
        self.assertIn("APPROVAL decide_react_task_block", workflow)
        self.assertIn('PERSIST ".lgwf/react_task_max_attempt_decision.json"', workflow)
        self.assertIn("ROUTE decide_react_task_block", workflow)
        self.assertIn('WHEN "reject" THEN resolve_max_attempt_decision', workflow)
        self.assertIn("FLOW resolve_max_attempt_decision", workflow)
        self.assertIn('WHEN "all_done" THEN finish_react_task_review', workflow)
        self.assertNotIn("THEN route_react_task_review\n  THEN finish_react_task_review", workflow)

    def test_resolve_max_attempt_decision_routes_user_choices(self) -> None:
        resolver = load_module("04_execute_react_loop/04_resolve/scripts/resolve_max_attempt_decision.py", "resolve_max_attempt")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            lgwf_dir.mkdir()
            plan = {
                "current_task_id": "task-1",
                "tasks": [
                    {"task_id": "task-1", "status": "blocked_for_user", "attempts": 3},
                    {"task_id": "task-2", "status": "acceptance_specified", "attempts": 0},
                ],
            }
            (lgwf_dir / "react_task_plan.json").write_text(json.dumps(plan), encoding="utf-8")
            (lgwf_dir / "react_task_route.json").write_text(
                json.dumps({"route": "requires_user_approval", "task_id": "task-1"}),
                encoding="utf-8",
            )

            for action, expected_route, expected_status in (
                ("continue", "continue_repair", "needs_repair"),
                ("skip", "move_next_task", "skipped"),
                ("accept", "move_next_task", "passed"),
                ("stop", "all_done", "stopped_by_user"),
                ("reject", "all_done", "stopped_by_user"),
            ):
                plan["tasks"][0]["status"] = "blocked_for_user"
                plan["tasks"][0]["attempts"] = 3
                plan["tasks"][1]["status"] = "acceptance_specified"
                plan["current_task_id"] = "task-1"
                (lgwf_dir / "react_task_plan.json").write_text(json.dumps(plan), encoding="utf-8")
                (lgwf_dir / "react_task_route.json").write_text(
                    json.dumps({"route": "requires_user_approval", "task_id": "task-1"}),
                    encoding="utf-8",
                )
                (lgwf_dir / "react_task_max_attempt_decision.json").write_text(
                    json.dumps({"action": action, "comment": "test decision"}),
                    encoding="utf-8",
                )

                output = io.StringIO()
                with pushd(root), redirect_stdout(output):
                    resolver.main()
                data = json.loads(output.getvalue())
                self.assertEqual(data["lgwf_plan.react_task_route"]["route"], expected_route)
                stored = json.loads((lgwf_dir / "react_task_plan.json").read_text(encoding="utf-8"))
                self.assertEqual(stored["tasks"][0]["status"], expected_status)
                if expected_route == "move_next_task":
                    self.assertEqual(stored["current_task_id"], "task-2")

            self.assertEqual(resolver.normalize_action({"value": {"action": "approve"}}), "accept")

    def test_route_script_emits_runtime_route_key(self) -> None:
        route = load_module("04_execute_react_loop/03_route/scripts/route_react_task_review.py", "route_react_task")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            lgwf_dir.mkdir()
            (lgwf_dir / "react_task_route.json").write_text(
                json.dumps({"route": "move_next_task", "task_id": "task-1"}),
                encoding="utf-8",
            )
            output = io.StringIO()
            with pushd(root), redirect_stdout(output):
                route.main()
            data = json.loads(output.getvalue())
            self.assertEqual(data["__route__route_react_task_review"], "move_next_task")
            self.assertEqual(data["lgwf_plan.next_route"], "move_next_task")

    def test_plan_generation_spec_defines_quality_contract(self) -> None:
        spec = (ROOT / "01_generate_plan/02_generate_plan_proposal/agents/spec.md").read_text(encoding="utf-8")
        for text in (
            "Plan Quality Criteria",
            "目标清晰",
            "输入输出明确",
            "产物可观察",
            "验收可判定",
            "human_approval_points",
            "react_points",
            "input_contract",
            "output_contract",
            "produced_artifacts",
        ):
            self.assertIn(text, spec)

    def test_plan_generation_spec_models_manual_approval_as_separate_tasks(self) -> None:
        spec = (ROOT / "01_generate_plan/02_generate_plan_proposal/agents/spec.md").read_text(encoding="utf-8")
        for text in (
            "Human Approval Task Modeling",
            "confirm_step_designs",
            "design_step_documents",
            "finalize_step_designs",
            ".lgwf/step_designs.json",
            "produced_artifacts",
            "acceptance_seed",
            "required_checks_hint",
        ):
            self.assertIn(text, spec)

    def test_acceptance_generation_spec_defines_quality_contract(self) -> None:
        spec = (ROOT / "02_generate_acceptance/00_generate_acceptance_proposal/agents/spec.md").read_text(encoding="utf-8")
        for text in (
            "Acceptance Quality Criteria",
            "证据可观察",
            "检查可执行",
            "判定明确",
            "negative_checks",
            "risk_checks",
            "evidence_requirements",
            "pass_condition",
            "fail_condition",
            "acceptance_goal",
        ):
            self.assertIn(text, spec)

    def test_acceptance_reason_is_compact_output_contract(self) -> None:
        spec = (ROOT / "02_generate_acceptance/00_generate_acceptance_proposal/agents/spec.md").read_text(encoding="utf-8")
        reason = (ROOT / "02_generate_acceptance/00_generate_acceptance_proposal/agents/reason.md").read_text(encoding="utf-8")
        act = (ROOT / "02_generate_acceptance/00_generate_acceptance_proposal/agents/act.md").read_text(encoding="utf-8")
        for text in (
            "compact_v1",
            "task_acceptance_index",
            "manual_gate_tasks",
            "global_check_principles",
            "完整 `required_checks`",
            "超过 20KB",
        ):
            self.assertIn(text, spec)
            self.assertIn(text, reason)
        self.assertIn("紧凑验收推理索引", act)
        self.assertIn("必须回到计划草案", act)

    def test_acceptance_generation_spec_keeps_confirmation_checks_after_approval(self) -> None:
        spec = (ROOT / "02_generate_acceptance/00_generate_acceptance_proposal/agents/spec.md").read_text(encoding="utf-8")
        for text in (
            "Human Approval Acceptance Modeling",
            "design_step_documents",
            "confirm_step_designs",
            "finalize_step_designs",
            ".lgwf/step_designs.json",
            "execute loop",
        ):
            self.assertIn(text, spec)
        design_section_start = spec.index("`design_step_documents`")
        confirm_section_start = spec.index("`confirm_step_designs`")
        design_section = spec[design_section_start:confirm_section_start]
        self.assertIn("设计文档草案", design_section)
        self.assertNotIn("step_design_confirmation_record", design_section)

    def test_execute_react_spec_defines_execution_quality_contract(self) -> None:
        spec = (ROOT / "04_execute_react_loop/01_implement_task/agents/spec.md").read_text(encoding="utf-8")
        for text in (
            "Execution Quality Criteria",
            "单 task 聚焦",
            "范围可追踪",
            "negative_check_results",
            "risk_check_results",
            "mapped_plan_step_indexes",
            "mapped_check_ids",
            "blocked_items",
            "不伪装通过",
        ):
            self.assertIn(text, spec)

    def test_execute_react_specs_define_manual_approval_block_contract(self) -> None:
        spec = (ROOT / "04_execute_react_loop/01_implement_task/agents/spec.md").read_text(encoding="utf-8")
        observe = (ROOT / "04_execute_react_loop/01_implement_task/agents/observe.md").read_text(encoding="utf-8")
        workflow = (ROOT / "04_execute_react_loop/workflow.lgwf").read_text(encoding="utf-8")
        for text in (
            "Manual Approval Blocks",
            "manual_approval_required",
            "required_follow_up",
            "approval_artifact",
            "confirmed_artifact",
            ".lgwf/step_design_confirmation_record.json",
            ".lgwf/step_designs.json",
        ):
            self.assertIn(text, spec)
            self.assertIn(text, observe)
        self.assertIn("业务门禁", workflow)
        self.assertIn("requires_user_approval", workflow)


    def test_execute_react_evidence_snapshot_contract(self) -> None:
        spec = (ROOT / "04_execute_react_loop/01_implement_task/agents/spec.md").read_text(encoding="utf-8")
        act = (ROOT / "04_execute_react_loop/01_implement_task/agents/act.md").read_text(encoding="utf-8")
        observe = (ROOT / "04_execute_react_loop/01_implement_task/agents/observe.md").read_text(encoding="utf-8")

        for text in ("content_summary", "content_excerpt"):
            self.assertIn(text, spec)
            self.assertIn(text, act)
            self.assertIn(text, observe)
        self.assertIn("不能只写路径", act)
        self.assertIn("不得仅因为不能直接读取本轮生成文件而 blocked", observe)


if __name__ == "__main__":
    unittest.main()
