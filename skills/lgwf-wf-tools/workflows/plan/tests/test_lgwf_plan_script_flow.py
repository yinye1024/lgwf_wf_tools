from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1] / "wf"


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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def call_script(relative: str, cwd: Path, name: str, expect_exit: bool = False) -> tuple[Any, str]:
    module = load_module(relative, name)
    output = io.StringIO()
    with pushd(cwd), redirect_stdout(output):
        try:
            module.main()
        except SystemExit as exc:
            if not expect_exit:
                raise
            return exc, output.getvalue()
    raw = output.getvalue().strip()
    return json.loads(raw) if raw else {}, raw


def task_plan(task_count: int = 5) -> dict:
    tasks = []
    for index in range(1, task_count + 1):
        tasks.append(
            {
                "task_id": f"task-{index}",
                "title": f"实现第 {index} 个任务",
                "task_role": "implementation_action",
                "execution_subject": "current_lgwf_plan_run",
                "produced_artifacts": [f"src/task_{index}.py"],
                "scope_detail": {"files": [f"src/task_{index}.py"]},
                "implementation_steps": [
                    f"创建 task-{index} 的输入契约",
                    f"实现 task-{index} 的可验收行为",
                ],
                "acceptance_seed": [f"task-{index} 有明确证据"],
                "required_checks_hint": ["python -m unittest"],
            }
        )
    return {
        "summary": {
            "problem_statement": "覆盖 lgwf-plan 的端到端计划、验收和执行分支。",
            "target_type": "modify_artifact",
            "proposed_approach": "构造五个独立 task，并按脚本契约推进成功、失败、重试、阻塞和完成路径。",
            "workflow_flow": [task["title"] for task in tasks],
            "key_decisions": [],
            "alternatives_considered": [],
            "open_questions": [],
            "quality_bar": ["所有 task 都有验收映射"],
        },
        "tasks": tasks,
    }


def acceptance_plan(plan: dict) -> dict:
    tasks = []
    for task in plan["tasks"]:
        tasks.append(
            {
                "task_id": task["task_id"],
                "criteria": [f"{task['task_id']} 完成"],
                "required_checks": ["python -m unittest"],
                "review_focus": ["仅检查当前 task 范围"],
                "out_of_scope": ["修改未声明文件"],
                "plan_validation_map": [
                    {
                        "plan_step_index": index,
                        "plan_step": step,
                        "expected_evidence": f"{task['task_id']} step {index} evidence",
                        "validation": "检查结果 JSON 和历史记录",
                    }
                    for index, step in enumerate(task["implementation_steps"])
                ],
            }
        )
    return {"tasks": tasks}


def pass_result(task_id: str) -> dict:
    return {
        "verdict": "pass",
        "pass": True,
        "accepted": True,
        "evidence": [f"{task_id} evidence"],
        "criteria_results": [{"criteria": f"{task_id} 完成", "passed": True}],
        "required_check_results": [{"check": "python -m unittest", "passed": True}],
        "negative_check_results": [{"check": "未修改未声明文件", "passed": True}],
        "risk_check_results": [{"risk": "范围漂移", "passed": True}],
        "plan_validation_results": [{"plan_step_index": 0, "passed": True}, {"plan_step_index": 1, "passed": True}],
        "scope_compliance": {"within_scope": True, "issues": []},
        "required_follow_up": [],
    }


def fail_result(attempt: int) -> dict:
    return {
        "verdict": "fail",
        "pass": False,
        "accepted": False,
        "evidence": [f"attempt {attempt} failed"],
        "required_follow_up": [f"修复 attempt {attempt} 的遗留问题"],
    }


def manual_approval_result() -> dict:
    return {
        "task_id": "task-1",
        "verdict": "fail",
        "pass": False,
        "accepted": False,
        "blocking_reason": "manual_approval_required",
        "evidence": [
            {"evidence_id": "step_design_confirmation_record_absent", "target": ".lgwf/step_design_confirmation_record.json"},
            {"evidence_id": "step_designs_json_absent", "target": ".lgwf/step_designs.json"},
        ],
        "criteria_results": [{"criterion": "需要人工确认步骤设计", "passed": False}],
        "required_check_results": [{"check_id": "check_step_design_confirmation", "passed": False}],
        "negative_check_results": [{"check_id": "negative_no_unapproved_design_as_input", "passed": True}],
        "risk_check_results": [{"risk": "未确认设计被当作实现输入", "passed": False}],
        "plan_validation_results": [{"plan_step_index": 3, "passed": False}],
        "scope_compliance": {"within_scope": True, "issues": []},
        "required_follow_up": [
            {
                "type": "approval",
                "title": "确认步骤设计",
                "reason": "步骤设计需要用户确认后才能固化",
                "locations": ["docs/steps/*.md"],
                "approval_artifact": ".lgwf/step_design_confirmation_record.json",
                "confirmed_artifact": ".lgwf/step_designs.json",
                "suggested_change": "进入人工确认节点，而不是继续 Codex 修复",
                "validation": "存在确认记录和确认后的 step_designs.json",
            }
        ],
    }


class LgwfPlanEndToEndTest(unittest.TestCase):
    def test_lgwf_plan_end_to_end_covers_all_branches_with_five_tasks(self) -> None:
        plan = task_plan(task_count=5)
        acceptance = acceptance_plan(plan)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"

            data, _ = call_script("04_execute_react_loop/03_route/scripts/route_react_task_review.py", root, "route_default_all_done")
            self.assertEqual(data["lgwf_plan.next_route"], "all_done")

            # 计划输入校验：失败分支与成功分支。
            write_json(lgwf_dir / "react_task_request.json", {"objective": "", "request": "", "analysis_target_files": []})
            _, output = call_script(
                "01_generate_plan/01_validate_plan_analysis_targets/scripts/validate_plan_analysis_targets.py",
                root,
                "validate_plan_bad",
                expect_exit=True,
            )
            self.assertIn("objective is required", output)

            write_json(
                lgwf_dir / "react_task_request.json",
                {
                    "objective": "设计 lgwf-plan 端到端测试",
                    "target_type": "modify_artifact",
                    "request": "覆盖全部分支，至少五个 task",
                    "analysis_target_files": ["workflow.lgwf"],
                    "analysis_target_dirs": ["04_execute_react_loop"],
                },
            )
            data, _ = call_script(
                "01_generate_plan/01_validate_plan_analysis_targets/scripts/validate_plan_analysis_targets.py",
                root,
                "validate_plan_ok",
            )
            self.assertTrue(data["lgwf_plan.plan_target_validation"]["passed"])

            # 计划生成：continue/failed 与 exit/ready 分支。
            write_json(lgwf_dir / "react_task_plan_proposal.json", {"tasks": []})
            write_json(lgwf_dir / "react_task_plan_observe.json", {"verdict": "fail", "issues": ["缺少任务"], "required_changes": ["补任务"]})
            data, _ = call_script("01_generate_plan/02_generate_plan_proposal/scripts/decide.py", root, "plan_decide_continue")
            self.assertEqual(data["next"], "continue")
            data, _ = call_script("01_generate_plan/03_route_plan_generation/scripts/route_plan_generation.py", root, "plan_route_failed")
            self.assertEqual(data["lgwf_plan.plan_generation_direction"]["status"], "plan_generation_failed")
            error, _ = call_script(
                "02_generate_acceptance/00_validate_acceptance_targets/scripts/validate_acceptance_codex_inputs.py",
                root,
                "validate_acceptance_bad",
                expect_exit=True,
            )
            self.assertIn("plan proposal requires non-empty tasks", str(error))

            write_json(lgwf_dir / "react_task_plan_proposal.json", plan)
            write_json(
                lgwf_dir / "react_task_plan_observe.json",
                {"verdict": "pass", "ready_for_acceptance_generation": True, "issues": [], "required_changes": []},
            )
            data, _ = call_script("01_generate_plan/02_generate_plan_proposal/scripts/decide.py", root, "plan_decide_exit")
            self.assertEqual(data["next"], "exit")
            data, _ = call_script("01_generate_plan/03_route_plan_generation/scripts/route_plan_generation.py", root, "plan_route_ready")
            self.assertEqual(data["lgwf_plan.plan_generation_direction"]["status"], "ready_for_acceptance")

            # 验收生成：前置校验、continue/failed 与 exit/ready 分支。
            data, _ = call_script(
                "02_generate_acceptance/00_validate_acceptance_targets/scripts/validate_acceptance_codex_inputs.py",
                root,
                "validate_acceptance_ok",
            )
            self.assertTrue(data["lgwf_plan.acceptance_inputs_valid"])

            write_json(lgwf_dir / "react_acceptance_proposal.json", {"tasks": []})
            write_json(
                lgwf_dir / "react_acceptance_observe.json",
                {
                    "verdict": "fail",
                    "acceptance_is_executable": False,
                    "plan_validation_map_complete": False,
                    "ready_for_confirmation": False,
                    "issues": ["验收不可执行"],
                    "required_changes": ["补齐映射"],
                },
            )
            data, _ = call_script("02_generate_acceptance/00_generate_acceptance_proposal/scripts/decide.py", root, "acceptance_decide_continue")
            self.assertEqual(data["next"], "continue")
            data, _ = call_script("02_generate_acceptance/01_route_acceptance_generation/scripts/route_acceptance_generation.py", root, "acceptance_route_failed")
            self.assertEqual(data["lgwf_plan.acceptance_generation_direction"]["status"], "acceptance_generation_failed")

            write_json(lgwf_dir / "react_acceptance_proposal.json", acceptance)
            write_json(
                lgwf_dir / "react_acceptance_observe.json",
                {
                    "verdict": "pass",
                    "acceptance_is_executable": True,
                    "plan_validation_map_complete": True,
                    "ready_for_confirmation": True,
                    "issues": [],
                    "required_changes": [],
                },
            )
            data, _ = call_script("02_generate_acceptance/00_generate_acceptance_proposal/scripts/decide.py", root, "acceptance_decide_exit")
            self.assertEqual(data["next"], "exit")
            data, _ = call_script("02_generate_acceptance/01_route_acceptance_generation/scripts/route_acceptance_generation.py", root, "acceptance_route_ready")
            self.assertEqual(data["lgwf_plan.acceptance_generation_direction"]["status"], "ready_for_confirmation")
            self.assertEqual(len(data["lgwf_plan.confirmation_context"]["tasks"]), 5)

            # 用户确认：reject 分支与 approve 后正式契约落盘。
            write_json(lgwf_dir / "react_task_contract_approval.json", {"decision": "reject"})
            data, _ = call_script(
                "03_confirm_plan_and_acceptance/01_apply_confirmed_contracts/scripts/finish_contract_review.py",
                root,
                "finish_rejected_contract",
            )
            self.assertTrue(data["lgwf_plan.contract_review_finished"])
            self.assertEqual(data["lgwf_plan.contract_review_finish"]["status"], "contract_revision_requested")
            self.assertFalse((lgwf_dir / "react_task_plan.json").exists())

            write_json(lgwf_dir / "react_task_contract_approval.json", {"decision": "approve"})
            data, _ = call_script(
                "03_confirm_plan_and_acceptance/01_apply_confirmed_contracts/scripts/apply_confirmed_contracts.py",
                root,
                "apply_approved",
            )
            self.assertTrue(data["lgwf_plan.contracts_applied"])
            self.assertEqual(len(read_json(lgwf_dir / "react_task_plan.json")["tasks"]), 5)

            # 执行循环：continue_repair、requires_user_approval、move_next_task、all_done。
            data, _ = call_script("04_execute_react_loop/00_prepare/scripts/prepare_react_task_review.py", root, "prepare_first")
            self.assertEqual(data["lgwf_plan.current_task_context"]["task"]["task_id"], "task-1")
            data, _ = call_script(
                "04_execute_react_loop/00_validate_execute_targets/scripts/validate_execute_codex_inputs.py",
                root,
                "validate_execute_task",
            )
            self.assertTrue(data["lgwf_plan.execute_inputs_valid"])

            for attempt in (1, 2):
                write_json(lgwf_dir / "react_task_result.json", fail_result(attempt))
                data, _ = call_script("04_execute_react_loop/01_implement_task/scripts/decide.py", root, f"execute_decide_continue_{attempt}")
                self.assertEqual(data["next"], "continue")
                data, _ = call_script("04_execute_react_loop/02_record/scripts/record_react_task_review.py", root, f"record_fail_{attempt}")
                self.assertEqual(data["lgwf_plan.react_task_route"]["route"], "continue_repair")
                data, _ = call_script("04_execute_react_loop/03_route/scripts/route_react_task_review.py", root, f"route_continue_{attempt}")
                self.assertEqual(data["lgwf_plan.next_route"], "continue_repair")
                call_script("04_execute_react_loop/00_prepare/scripts/prepare_react_task_review.py", root, f"prepare_repair_{attempt}")

            write_json(lgwf_dir / "react_task_result.json", fail_result(3))
            data, _ = call_script("04_execute_react_loop/02_record/scripts/record_react_task_review.py", root, "record_blocked")
            self.assertEqual(data["lgwf_plan.react_task_route"]["route"], "requires_user_approval")
            data, _ = call_script("04_execute_react_loop/03_route/scripts/route_react_task_review.py", root, "route_blocked")
            self.assertEqual(data["lgwf_plan.next_route"], "requires_user_approval")
            write_json(lgwf_dir / "react_task_max_attempt_decision.json", {"action": "continue", "comment": "script flow repair"})
            data, _ = call_script(
                "04_execute_react_loop/04_resolve/scripts/resolve_max_attempt_decision.py",
                root,
                "resolve_blocked_continue",
            )
            self.assertEqual(data["lgwf_plan.react_task_route"]["route"], "continue_repair")
            data, _ = call_script("04_execute_react_loop/03_route/scripts/route_react_task_review.py", root, "route_resolved_continue")
            self.assertEqual(data["lgwf_plan.next_route"], "continue_repair")

            for task_index in range(1, 6):
                call_script("04_execute_react_loop/00_prepare/scripts/prepare_react_task_review.py", root, f"prepare_pass_{task_index}")
                write_json(lgwf_dir / "react_task_result.json", pass_result(f"task-{task_index}"))
                data, _ = call_script("04_execute_react_loop/01_implement_task/scripts/decide.py", root, f"execute_decide_exit_{task_index}")
                self.assertEqual(data["next"], "exit")
                data, _ = call_script("04_execute_react_loop/02_record/scripts/record_react_task_review.py", root, f"record_pass_{task_index}")
                expected_route = "all_done" if task_index == 5 else "move_next_task"
                self.assertEqual(data["lgwf_plan.react_task_route"]["route"], expected_route)
                data, _ = call_script("04_execute_react_loop/03_route/scripts/route_react_task_review.py", root, f"route_pass_{task_index}")
                self.assertEqual(data["lgwf_plan.next_route"], expected_route)

            data, _ = call_script("04_execute_react_loop/00_prepare/scripts/prepare_react_task_review.py", root, "prepare_all_done")
            self.assertTrue(data["lgwf_plan.current_task_context"]["all_done"])
            data, _ = call_script(
                "04_execute_react_loop/00_validate_execute_targets/scripts/validate_execute_codex_inputs.py",
                root,
                "validate_execute_all_done",
            )
            self.assertTrue(data["lgwf_plan.execute_inputs_valid"])
            data, _ = call_script("04_execute_react_loop/02_record/scripts/record_react_task_review.py", root, "record_all_done_context")
            self.assertEqual(data["lgwf_plan.react_task_route"]["route"], "all_done")

            data, _ = call_script("04_execute_react_loop/05_finish/scripts/finish_react_task_review.py", root, "finish_report")
            self.assertTrue(data["lgwf_plan.finished"])
            self.assertEqual(data["lgwf_plan.report"]["history_count"], 9)
            self.assertTrue((root / "reports" / "react-task" / "react_task_report.json").exists())

    def test_manual_approval_block_routes_to_user_without_repair_loop(self) -> None:
        plan = task_plan(task_count=1)
        acceptance = acceptance_plan(plan)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "react_task_plan.json", plan)
            write_json(lgwf_dir / "react_acceptance_plan.json", acceptance)

            data, _ = call_script("04_execute_react_loop/00_prepare/scripts/prepare_react_task_review.py", root, "prepare_manual_block")
            self.assertEqual(data["lgwf_plan.current_task_context"]["task"]["task_id"], "task-1")

            write_json(lgwf_dir / "react_task_result.json", manual_approval_result())
            data, _ = call_script("04_execute_react_loop/02_record/scripts/record_react_task_review.py", root, "record_manual_block")
            route = data["lgwf_plan.react_task_route"]
            self.assertEqual(route["route"], "requires_user_approval")
            self.assertEqual(route["status"], "blocked_for_user")
            self.assertEqual(route["attempts"], 1)

            stored_plan = read_json(lgwf_dir / "react_task_plan.json")
            self.assertEqual(stored_plan["tasks"][0]["attempts"], 1)
            self.assertEqual(stored_plan["tasks"][0]["status"], "blocked_for_user")

            data, _ = call_script("04_execute_react_loop/03_route/scripts/route_react_task_review.py", root, "route_manual_block")
            self.assertEqual(data["lgwf_plan.next_route"], "requires_user_approval")

    def test_manual_approval_block_exits_react_before_internal_max_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "react_task_result.json", manual_approval_result())
            data, _ = call_script("04_execute_react_loop/01_implement_task/scripts/decide.py", root, "decide_manual_block")
            self.assertEqual(data["next"], "exit")

            write_json(lgwf_dir / "react_task_result.json", fail_result(1))
            data, _ = call_script("04_execute_react_loop/01_implement_task/scripts/decide.py", root, "decide_regular_fail")
            self.assertEqual(data["next"], "continue")

    def test_legacy_step_design_missing_artifacts_route_to_user(self) -> None:
        plan = task_plan(task_count=1)
        acceptance = acceptance_plan(plan)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "react_task_plan.json", plan)
            write_json(lgwf_dir / "react_acceptance_plan.json", acceptance)
            call_script("04_execute_react_loop/00_prepare/scripts/prepare_react_task_review.py", root, "prepare_legacy_manual_block")

            legacy_result = fail_result(1)
            legacy_result["required_check_results"] = [
                {"check_id": "check_step_design_confirmation", "passed": False}
            ]
            legacy_result["evidence"] = [
                {"evidence_id": "step_design_confirmation_record_absent"},
                {"evidence_id": "step_designs_json_absent"},
            ]
            legacy_result["required_follow_up"] = [
                {
                    "title": "提交步骤设计给用户确认",
                    "reason": "缺少确认记录",
                    "locations": ["docs/steps/*.md"],
                    "suggested_change": "进入 APPROVAL",
                    "validation": "检查 .lgwf/step_designs.json",
                }
            ]
            write_json(lgwf_dir / "react_task_result.json", legacy_result)

            data, _ = call_script("04_execute_react_loop/02_record/scripts/record_react_task_review.py", root, "record_legacy_manual_block")
            self.assertEqual(data["lgwf_plan.react_task_route"]["route"], "requires_user_approval")
            self.assertEqual(read_json(lgwf_dir / "react_task_plan.json")["tasks"][0]["attempts"], 1)

    def test_rejected_initial_task_request_finishes_without_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "react_task_request.json", {"decision": "reject", "comment": "stop before planning"})

            data, _ = call_script(
                "01_generate_plan/00_collect_react_task_request/scripts/finish_react_task_request.py",
                root,
                "finish_rejected_task_request",
            )

            self.assertTrue(data["lgwf_plan.task_request_finished"])
            self.assertEqual(data["lgwf_plan.task_request_finish"]["status"], "task_request_rejected")
            self.assertFalse((lgwf_dir / "react_task_plan_proposal.json").exists())

    def test_rejected_react_block_decision_stops_by_business_route(self) -> None:
        plan = task_plan(task_count=1)
        acceptance = acceptance_plan(plan)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "react_task_plan.json", plan)
            write_json(lgwf_dir / "react_acceptance_plan.json", acceptance)
            write_json(lgwf_dir / "react_task_route.json", {"route": "requires_user_approval", "task_id": "task-1"})
            write_json(lgwf_dir / "react_task_max_attempt_decision.json", {"decision": "reject", "comment": "stop task"})

            data, _ = call_script(
                "04_execute_react_loop/04_resolve/scripts/resolve_max_attempt_decision.py",
                root,
                "resolve_rejected_block_decision",
            )

            self.assertEqual(data["lgwf_plan.react_task_route"]["route"], "all_done")
            self.assertEqual(data["lgwf_plan.react_task_route"]["status"], "stopped_by_user")

    def test_approve_react_block_decision_continues_repair_not_passes(self) -> None:
        plan = task_plan(task_count=1)
        acceptance = acceptance_plan(plan)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "react_task_plan.json", plan)
            write_json(lgwf_dir / "react_acceptance_plan.json", acceptance)
            write_json(lgwf_dir / "react_task_route.json", {"route": "requires_user_approval", "task_id": "task-1"})
            write_json(lgwf_dir / "react_task_max_attempt_decision.json", {"action": "approve", "comment": "继续处理"})

            data, _ = call_script(
                "04_execute_react_loop/04_resolve/scripts/resolve_max_attempt_decision.py",
                root,
                "resolve_approve_as_continue",
            )

            self.assertEqual(data["lgwf_plan.react_task_route"]["route"], "continue_repair")
            stored_plan = read_json(lgwf_dir / "react_task_plan.json")
            self.assertEqual(stored_plan["tasks"][0]["status"], "needs_repair")
            self.assertEqual(stored_plan["current_task_id"], "task-1")

    def test_business_artifact_block_cannot_be_accepted_without_artifacts(self) -> None:
        plan = task_plan(task_count=2)
        acceptance = acceptance_plan(plan)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "react_task_plan.json", plan)
            write_json(lgwf_dir / "react_acceptance_plan.json", acceptance)
            write_json(lgwf_dir / "react_task_route.json", {"route": "requires_user_approval", "task_id": "task-1"})
            write_json(
                lgwf_dir / "react_task_result.json",
                {
                    "task_id": "task-1",
                    "verdict": "blocked",
                    "pass": False,
                    "required_follow_up": [
                        {
                            "type": "approval",
                            "approval_artifact": "ws/.lgwf/create_requirements_approval.json",
                            "confirmed_artifact": "ws/.lgwf/create_requirements.json",
                        }
                    ],
                },
            )
            write_json(lgwf_dir / "react_task_max_attempt_decision.json", {"action": "accept", "comment": "错误接受"})

            data, _ = call_script(
                "04_execute_react_loop/04_resolve/scripts/resolve_max_attempt_decision.py",
                root,
                "resolve_business_block_missing_artifacts",
            )

            route = data["lgwf_plan.react_task_route"]
            self.assertEqual(route["route"], "requires_user_approval")
            self.assertEqual(route["status"], "blocked_for_user")
            self.assertEqual(
                route["missing_artifacts"],
                [
                    "ws/.lgwf/create_requirements_approval.json",
                    "ws/.lgwf/create_requirements.json",
                ],
            )
            stored_plan = read_json(lgwf_dir / "react_task_plan.json")
            self.assertEqual(stored_plan["tasks"][0]["status"], "blocked_for_user")
            self.assertEqual(stored_plan["current_task_id"], "task-1")

    def test_create_artifact_plan_rejects_generated_artifact_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(
                lgwf_dir / "react_task_request.json",
                {
                    "objective": "创建 workflow skill",
                    "target_type": "create_artifact",
                    "request": "生成一个新的 workflow package",
                    "analysis_target_dirs": ["skills"],
                    "analysis_target_files": [],
                },
            )
            write_json(
                lgwf_dir / "react_task_plan_proposal.json",
                {
                    "summary": {"target_type": "create_artifact"},
                    "tasks": [
                        {
                            "task_id": "collect_raw_intent",
                            "title": "收集原始意图",
                            "task_role": "generated_artifact_behavior",
                            "execution_subject": "generated_artifact_runtime",
                            "produced_artifacts": [],
                            "implementation_plan": "运行未来 workflow 的收集节点",
                        }
                    ],
                },
            )
            write_json(
                lgwf_dir / "react_task_plan_observe.json",
                {"verdict": "pass", "ready_for_acceptance_generation": True},
            )

            data, _ = call_script("01_generate_plan/02_generate_plan_proposal/scripts/decide.py", root, "plan_decide_safety_fail")

            self.assertEqual(data["next"], "continue")
            self.assertFalse(data["plan_contract_safety"]["passed"])
            self.assertEqual(
                data["plan_contract_safety"]["issues"][0]["code"],
                "generated_artifact_behavior_in_current_plan",
            )

    def test_apply_contracts_rejects_unsafe_create_artifact_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf_dir = root / ".lgwf"
            write_json(lgwf_dir / "react_task_request.json", {"target_type": "create_artifact"})
            write_json(
                lgwf_dir / "react_task_plan_proposal.json",
                {
                    "summary": {"target_type": "create_artifact"},
                    "tasks": [
                        {
                            "task_id": "confirm_requirements",
                            "task_role": "generated_artifact_behavior",
                            "execution_subject": "future_runtime",
                            "implementation_steps": [],
                            "produced_artifacts": [],
                        }
                    ],
                },
            )
            write_json(lgwf_dir / "react_acceptance_proposal.json", {"tasks": [{"task_id": "confirm_requirements"}]})
            write_json(lgwf_dir / "react_task_contract_approval.json", {"approval": "approve"})

            error, _ = call_script(
                "03_confirm_plan_and_acceptance/01_apply_confirmed_contracts/scripts/apply_confirmed_contracts.py",
                root,
                "apply_unsafe_create_artifact",
                expect_exit=True,
            )

            self.assertIn("plan contract safety check failed", str(error))
            self.assertFalse((lgwf_dir / "react_task_plan.json").exists())


if __name__ == "__main__":
    unittest.main()
