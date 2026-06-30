from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(relative: str, name: str):
    path = ROOT / "wf" / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@contextmanager
def pushd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class SelfFixScriptsTest(unittest.TestCase):
    def test_repair_loop_uses_agent_loop_standard_chain(self) -> None:
        source = (ROOT / "wf" / "03_repair_target_agent_loop" / "workflow.lgwf").read_text(encoding="utf-8")
        for node in (
            "PY prepare_repair_agent_loop",
            "AGENT_LOOP repair_target MAX_ITERATIONS 5",
            "OBSERVE PY observe_repair_context",
            "DIAGNOSE CODEX diagnose_target_failure",
            "PLAN CODEX propose_repair_plan",
            "ACT CODEX apply_repair_plan",
            "VERIFY WORKFLOW verify_repair_candidate_with_review",
            "DECIDE PY decide_repair_loop",
            "PY route_after_repair_agent_loop",
            "PY promote_repair_candidate",
        ):
            self.assertIn(node, source)
        self.assertIn('WORKFLOW "05_fix_target/verify_repair_candidate_workflow.lgwf"', source)
        self.assertIn("RESULT state.lgwf_wf_fix.target_repair_current_verification", source)
        self.assertIn("WHEN \"fix\" THEN prepare_repair_agent_loop", source)
        self.assertIn(
            "FLOW prepare_repair_agent_loop\n"
            "  THEN repair_target\n"
            "  THEN route_after_repair_agent_loop;",
            source,
        )
        self.assertIn(
            "ROUTE route_after_repair_agent_loop\n"
            "  WHEN \"promote\" THEN promote_repair_candidate\n"
            "  WHEN \"finish\" THEN finish_self_fix;",
            source,
        )
        self.assertIn(
            "FLOW promote_repair_candidate\n"
            "  THEN record_fix_attempt\n"
            "  THEN run_target_workflow;",
            source,
        )
        self.assertNotIn(
            "validate_repair\n"
            "  THEN record_fix_attempt\n"
            "  THEN run_target_workflow;",
            source,
        )
        self.assertNotIn("CODEX review_repair_plan", source)
        self.assertNotIn("PY route_after_plan", source)
        self.assertNotIn("PY route_after_repair\n", source)
        self.assertNotIn("CODEX fix_target_workflow", source)
        self.assertIn('ARTIFACTS ".lgwf/loops/repair_target"', source)
        self.assertIn("ON_MAX wait_human", source)
        self.assertIn("ON_ERROR wait_human", source)

    def test_verify_repair_candidate_workflow_runs_review_only_when_needed(self) -> None:
        source = (
            ROOT
            / "wf"
            / "03_repair_target_agent_loop"
            / "05_fix_target"
            / "verify_repair_candidate_workflow.lgwf"
        ).read_text(encoding="utf-8")
        self.assertIn("PY verify_repair_candidate", source)
        self.assertIn("PY route_after_verification", source)
        self.assertIn("CODEX review_repair_candidate", source)
        self.assertIn("PY finalize_repair_candidate_review", source)
        self.assertIn('WHEN "review" THEN review_repair_candidate', source)
        self.assertIn('WHEN "finish" THEN finalize_repair_candidate_review', source)
        self.assertIn("TARGET_DIRS state.targets.dirs", source)
        self.assertIn("TARGET_FILES state.targets.files", source)

    def test_repair_prompts_cover_contract_drift(self) -> None:
        agents = ROOT / "wf" / "03_repair_target_agent_loop" / "05_fix_target" / "agents"
        for name in (
            "diagnose_target_failure.md",
            "propose_repair_plan.md",
            "apply_repair_plan.md",
        ):
            source = (agents / name).read_text(encoding="utf-8")
            self.assertIn("target_repair/current", source)
            self.assertIn("observation.json", source)
            self.assertIn("contract_drift", source)
            if name != "apply_repair_plan.md":
                self.assertIn("output_contract", source)

    def test_repair_agent_loop_prompts_define_quality_contracts(self) -> None:
        agents = ROOT / "wf" / "03_repair_target_agent_loop" / "05_fix_target" / "agents"

        diagnose = (agents / "diagnose_target_failure.md").read_text(encoding="utf-8")
        self.assertIn("Diagnosis Quality Criteria", diagnose)
        self.assertIn("证据可追溯", diagnose)
        self.assertIn("区分症状和根因", diagnose)
        self.assertIn("confidence", diagnose)
        self.assertIn("excluded_causes", diagnose)
        self.assertIn("repair_scope", diagnose)

        plan = (agents / "propose_repair_plan.md").read_text(encoding="utf-8")
        self.assertIn("Repair Plan Quality Criteria", plan)
        self.assertIn("根因对齐", plan)
        self.assertIn("最小完整", plan)
        self.assertIn("可验证", plan)
        self.assertIn("plan_steps", plan)
        self.assertIn("files_to_modify", plan)
        self.assertIn("expected_evidence", plan)

        apply = (agents / "apply_repair_plan.md").read_text(encoding="utf-8")
        self.assertIn("Repair Application Quality Criteria", apply)
        self.assertIn("计划一致", apply)
        self.assertIn("沙箱隔离", apply)
        self.assertIn("范围可审计", apply)
        self.assertIn("changed_files", apply)
        self.assertIn("plan_step_results", apply)
        self.assertIn("scope_confirmation", apply)

    def test_root_workflow_wraps_repair_loop_as_subworkflow(self) -> None:
        source = (ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn('PROMPT "01_prepare_target/agents/analyze_target_input_contract.md"', source)
        self.assertNotIn("02_collect_target_input", source)
        self.assertNotIn("02_prompt_acceptance", source)
        self.assertNotIn("choose_prompt_acceptance", source)
        self.assertIn('STEP repair_target_loop\n  WORKFLOW "03_repair_target_agent_loop/workflow.lgwf";', source)
        self.assertIn('PY summarize_self_fix\n  SCRIPT "04_summarize_self_fix/scripts/summarize_self_fix.py"', source)
        self.assertIn("THEN repair_target_loop\n  THEN summarize_self_fix;", source)
        for node in (
            "PY run_target_workflow",
            "PY observe_target_run",
            "APPROVAL proxy_target_approval",
            "CODEX fix_target_workflow",
            "PY route_after_observe",
        ):
            self.assertNotIn(node, source)

    def test_summary_extracts_runtime_tokens_issues_fixes_and_files(self) -> None:
        summarize = load_module("04_summarize_self_fix/scripts/summarize_self_fix.py", "summarize_self_fix")
        started = datetime(2026, 6, 19, 10, 0, tzinfo=UTC)
        finished = started + timedelta(minutes=7, seconds=30)
        summary = summarize.build_summary(
            target={
                "target_workflow_lgwf": "target/workflow.lgwf",
                "last_status": "succeeded",
                "current_attempt": 2,
                "max_attempts": 5,
            },
            history=[
                {"event": "target_started", "attempt": 1, "ts": started.isoformat()},
                {"event": "target_failed", "attempt": 1, "phase": "failed", "ts": (started + timedelta(minutes=2)).isoformat()},
                {"event": "target_started", "attempt": 2, "ts": (started + timedelta(minutes=5)).isoformat()},
                {"event": "target_succeeded", "attempt": 2, "ts": finished.isoformat()},
            ],
            failure_review={
                "phase": "failed",
                "status": {"last_error": "missing script"},
                "run_artifacts": {
                    "changed_stdout": json.dumps({"changed_files": ["wf/workflow.lgwf"]}),
                    "summary_stdout": json.dumps({"usage": {"total_tokens": 1234}}),
                },
            },
            fix_notes="Moved missing script into workflow package.",
        )
        self.assertEqual(summary["status"], "success_clean")
        self.assertEqual(summary["duration_seconds"], 450)
        self.assertEqual(summary["token_usage"]["total_tokens"], 1234)
        self.assertEqual(summary["issues_found"][0]["error"], "missing script")
        self.assertEqual(summary["fixes_applied"], ["Moved missing script into workflow package."])
        self.assertEqual(summary["changed_files"], ["wf/workflow.lgwf"])

    def test_summary_marks_successful_target_with_stale_output_contract_as_needs_repair(self) -> None:
        summarize = load_module("04_summarize_self_fix/scripts/summarize_self_fix.py", "summarize_contract")
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp)
            workflow = attempt / ".lgwf" / "workflow" / "workflow.lgwf"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "WORKFLOW demo;\n"
                "ENTRY analyze_stock_1;\n"
                "STEP analyze_stock_1 WORKFLOW \"02_analyze_stock_1/workflow.lgwf\";\n"
                "FLOW analyze_stock_1;\n",
                encoding="utf-8",
            )
            report = attempt / "reports" / "final_summary.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "stock_reports": [
                            {"stock": "stock_1", "analysis_exists": True, "review_exists": True},
                            {"stock": "stock_2", "analysis_exists": False, "review_exists": False},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            summary = summarize.build_summary(
                target={
                    "target_workflow_lgwf": "target/workflow.lgwf",
                    "last_status": "succeeded",
                    "current_attempt": 1,
                    "max_attempts": 5,
                    "last_attempt_dir": str(attempt),
                },
                history=[],
                failure_review={},
                fix_notes="",
            )
        self.assertEqual(summary["status"], "needs_repair")
        self.assertEqual(summary["issues_found"][0]["phase"], "contract_drift")
        self.assertIn("stock_2", summary["issues_found"][0]["error"])

    def test_summary_preserves_needs_repair_status(self) -> None:
        summarize = load_module("04_summarize_self_fix/scripts/summarize_self_fix.py", "summarize_needs_repair")
        summary = summarize.build_summary(
            target={
                "target_workflow_lgwf": "target/workflow.lgwf",
                "last_status": "needs_repair",
                "current_attempt": 1,
                "max_attempts": 5,
            },
            history=[],
            failure_review={"phase": "contract_drift", "error": "stale output contract"},
            fix_notes="",
        )
        self.assertEqual(summary["status"], "needs_repair")

    def test_summary_collects_run_health_warnings_and_compresses_repeated_history(self) -> None:
        summarize = load_module("04_summarize_self_fix/scripts/summarize_self_fix.py", "summarize_health")
        started = datetime(2026, 6, 19, 10, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp)
            data = attempt / "data" / "top_decliners.json"
            data.parent.mkdir(parents=True)
            data.write_text(
                json.dumps({"method": "Fallback: kline endpoints were unavailable."}),
                encoding="utf-8",
            )
            stderr = attempt / ".lgwf" / "codex" / "node-001" / "stderr.txt"
            stderr.parent.mkdir(parents=True)
            stderr.write_text(
                "stream disconnected - retrying sampling request (5/5)\nfalling back to HTTP\n",
                encoding="utf-8",
            )
            history = [
                {"event": "target_still_running", "attempt": 1, "ts": (started + timedelta(seconds=i)).isoformat()}
                for i in range(3)
            ]
            history.append({"event": "target_succeeded", "attempt": 1, "ts": (started + timedelta(seconds=5)).isoformat()})
            summary = summarize.build_summary(
                target={
                    "target_workflow_lgwf": "target/workflow.lgwf",
                    "last_status": "succeeded",
                    "current_attempt": 1,
                    "max_attempts": 5,
                    "last_attempt_dir": str(attempt),
                },
                history=history,
                failure_review={},
                fix_notes="",
            )
        self.assertEqual(summary["status"], "success_degraded")
        self.assertEqual(summary["run_health"]["codex_stream_disconnects"], 1)
        self.assertEqual(summary["run_health"]["codex_http_fallbacks"], 1)
        self.assertTrue(summary["run_health"]["data_fallback"])
        self.assertEqual(summary["history_events"][0]["event"], "target_running_poll")
        self.assertEqual(summary["history_events"][0]["count"], 3)

    def test_contract_audit_prefers_explicit_contract_required_files(self) -> None:
        inspection = load_module("shared/self_fix_inspection.py", "inspection_contract")
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp)
            contract = attempt / ".lgwf" / "workflow" / ".lgwf-contract.json"
            contract.parent.mkdir(parents=True)
            contract.write_text(
                json.dumps({"required_files": ["reports/stock_1/analysis.md", "reports/stock_1/review.md"]}),
                encoding="utf-8",
            )
            final_summary = attempt / "reports" / "final_summary.json"
            final_summary.parent.mkdir(parents=True)
            final_summary.write_text(
                json.dumps(
                    {
                        "stock_reports": [
                            {"stock": "stock_2", "analysis_exists": False, "review_exists": False}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (attempt / "reports" / "stock_1").mkdir(parents=True)
            (attempt / "reports" / "stock_1" / "analysis.md").write_text("ok", encoding="utf-8")
            audit = inspection.collect_contract_audit(attempt)
        self.assertTrue(audit["explicit_contract"])
        self.assertEqual(audit["issues"][0]["phase"], "output_contract")
        self.assertIn("reports/stock_1/review.md", audit["issues"][0]["error"])
        self.assertEqual(audit["stale_expectations"], [])

    def test_contract_audit_lists_unscheduled_final_summary_expectations(self) -> None:
        inspection = load_module("shared/self_fix_inspection.py", "inspection_audit")
        with tempfile.TemporaryDirectory() as temp:
            attempt = Path(temp)
            workflow = attempt / ".lgwf" / "workflow" / "workflow.lgwf"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "WORKFLOW demo;\n"
                "STEP analyze_stock_1 WORKFLOW \"02_analyze_stock_1/workflow.lgwf\";\n"
                "FLOW analyze_stock_1;\n",
                encoding="utf-8",
            )
            report = attempt / "reports" / "final_summary.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "stock_reports": [
                            {"stock": "stock_1", "analysis_exists": True, "review_exists": True},
                            {"stock": "stock_2", "analysis_exists": False, "review_exists": False},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            audit = inspection.collect_contract_audit(attempt)
        self.assertFalse(audit["explicit_contract"])
        self.assertEqual(audit["scheduled_ids"], ["stock_1"])
        self.assertEqual(audit["final_summary_expected"], ["stock_1", "stock_2"])
        self.assertEqual(audit["stale_expectations"][0]["id"], "stock_2")
        self.assertEqual(audit["issues"][0]["phase"], "contract_drift")

    def test_observe_routes_successful_target_with_contract_drift_to_fix(self) -> None:
        observe = load_module("03_repair_target_agent_loop/04_observe_target/scripts/observe_target_run.py", "observe_contract")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf = root / ".lgwf"
            lgwf.mkdir()
            attempt = root / "attempt-001"
            workflow = attempt / ".lgwf" / "workflow" / "workflow.lgwf"
            workflow.parent.mkdir(parents=True)
            workflow.write_text(
                "WORKFLOW demo;\n"
                "ENTRY analyze_stock_1;\n"
                "STEP analyze_stock_1 WORKFLOW \"02_analyze_stock_1/workflow.lgwf\";\n"
                "FLOW analyze_stock_1;\n",
                encoding="utf-8",
            )
            report = attempt / "reports" / "final_summary.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "stock_reports": [
                            {"stock": "stock_1", "analysis_exists": True, "review_exists": True},
                            {"stock": "stock_2", "analysis_exists": False, "review_exists": False},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            log_file = attempt / "target-workflow.log"
            log_file.write_text("target completed\n", encoding="utf-8")
            target = {"current_attempt": 1, "max_attempts": 5, "last_attempt_dir": str(attempt)}
            with pushd(root):
                result = observe.handle_completed_target(
                    lgwf_root=lgwf,
                    target=target,
                    work_dir=attempt,
                    log_file=log_file,
                    status={"phase": "completed"},
                    run_artifacts={"latest_run": {"run_id": "run-1"}},
                )
            review = json.loads((lgwf / "target_repair" / "current" / "observation.json").read_text(encoding="utf-8"))
            saved_target = json.loads((lgwf / "self_fix_target.json").read_text(encoding="utf-8"))
        self.assertEqual(result["next_action"], "fix")
        self.assertEqual(saved_target["last_status"], "needs_repair")
        self.assertEqual(review["phase"], "contract_drift")
        self.assertIn("contract_audit", review)
        self.assertIn("contract_drift", {issue["phase"] for issue in review["issues"]})

    def test_observe_finishes_successful_target_with_only_run_health_warnings(self) -> None:
        observe = load_module("03_repair_target_agent_loop/04_observe_target/scripts/observe_target_run.py", "observe_health")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lgwf = root / ".lgwf"
            lgwf.mkdir()
            attempt = root / "attempt-001"
            data = attempt / "data" / "top_decliners.json"
            data.parent.mkdir(parents=True)
            data.write_text(json.dumps({"method": "Fallback: latest day data."}), encoding="utf-8")
            stderr = attempt / ".lgwf" / "codex" / "node-001" / "stderr.txt"
            stderr.parent.mkdir(parents=True)
            stderr.write_text("stream disconnected\nfalling back to HTTP\n", encoding="utf-8")
            log_file = attempt / "target-workflow.log"
            log_file.write_text("target completed\n", encoding="utf-8")
            target = {"current_attempt": 1, "max_attempts": 5, "last_attempt_dir": str(attempt)}
            with pushd(root):
                result = observe.handle_completed_target(
                    lgwf_root=lgwf,
                    target=target,
                    work_dir=attempt,
                    log_file=log_file,
                    status={"phase": "completed"},
                    run_artifacts={"latest_run": {"run_id": "run-1"}},
                )
            observation = json.loads((lgwf / "target_repair" / "current" / "observation.json").read_text(encoding="utf-8"))
            health = observation["run_health"]
            saved_target = json.loads((lgwf / "self_fix_target.json").read_text(encoding="utf-8"))
        self.assertEqual(result["next_action"], "finish")
        self.assertEqual(saved_target["last_status"], "succeeded")
        self.assertTrue(health["data_fallback"])
        self.assertEqual(health["codex_stream_disconnects"], 1)
        self.assertEqual(health["codex_http_fallbacks"], 1)

    def test_observe_treats_failed_latest_run_as_failed_when_process_stopped(self) -> None:
        observe = load_module(
            "03_repair_target_agent_loop/04_observe_target/scripts/observe_target_run.py",
            "observe_failed_latest_run",
        )
        self.assertTrue(observe.latest_run_failed({"latest_run": {"status": "failed"}}))
        self.assertFalse(observe.latest_run_failed({"latest_run": {"status": "completed"}}))
        self.assertFalse(observe.latest_run_failed({}))

    def test_observe_finds_pending_target_approval_when_status_omits_it(self) -> None:
        observe = load_module(
            "03_repair_target_agent_loop/04_observe_target/scripts/observe_target_run.py",
            "observe_pending_approval",
        )
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            human_dir = work_dir / ".lgwf" / "human"
            human_dir.mkdir(parents=True)
            (human_dir / "human-complete.request.json").write_text(
                json.dumps({"request_id": "human-complete", "status": "pending"}),
                encoding="utf-8",
            )
            (human_dir / "human-complete.response.json").write_text("{}", encoding="utf-8")
            (human_dir / "human-pending.request.json").write_text(
                json.dumps({"request_id": "human-pending", "status": "pending"}),
                encoding="utf-8",
            )

            request = observe.find_pending_human_request(work_dir)

        self.assertEqual(request["request_id"], "human-pending")

    def test_validate_repair_records_failed_static_checks(self) -> None:
        validate = load_module("03_repair_target_agent_loop/05_fix_target/scripts/validate_repair.py", "validate_repair")

        @dataclass
        class Result:
            returncode: int
            stdout: str = ""
            stderr: str = ""

        calls: list[list[str]] = []

        def fake_run(args: list[str], *, timeout: int = 120):
            calls.append(args)
            if args[0] == "audit":
                return Result(1, "", "audit failed")
            if args[0] == "compile":
                return Result(0, "{}")
            raise AssertionError(args)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "target"
            package.mkdir()
            workflow = package / "workflow.lgwf"
            workflow.write_text("WORKFLOW target;\nENTRY done;\n", encoding="utf-8")
            result = validate.validate_target_repair(
                {
                    "target_workflow_lgwf": str(workflow),
                    "target_package_root": str(package),
                },
                run_lgwf_func=fake_run,
                compileall_func=lambda path: Result(0, ""),
            )
        self.assertFalse(result["passed"])
        self.assertEqual(result["issues"][0]["check"], "audit")
        self.assertEqual(result["issues"][0]["stderr"], "audit failed")
        self.assertEqual([call[0] for call in calls], ["audit", "compile"])

    def test_route_after_repair_blocks_rerun_when_plan_or_validation_fails(self) -> None:
        route = load_module("03_repair_target_agent_loop/05_fix_target/scripts/route_after_repair_agent_loop.py", "route_after_repair_agent_loop")
        self.assertEqual(route.choose_route({"status": "finished", "stop_reason": "repair_candidate_ready"}), "promote")
        self.assertEqual(route.choose_route({"status": "blocked", "stop_reason": "validation_failed"}), "finish")
        self.assertEqual(route.choose_route({"status": "waiting_human", "stop_reason": "max_attempts_reached"}), "finish")

    def test_target_repair_loop_initializes_current_workspace(self) -> None:
        loop = load_module("shared/target_repair_loop.py", "target_loop_init")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / ".lgwf"
            state = loop.start_iteration(root, {"current_attempt": 1, "max_attempts": 5})
            loop_root = root / "target_repair"
            self.assertEqual(state["status"], "running")
            self.assertEqual(state["current_iteration"], 1)
            self.assertEqual(state["phase"], "run")
            self.assertTrue((loop_root / "loop.json").exists())
            self.assertTrue((loop_root / "current").is_dir())
            self.assertEqual(json.loads((loop_root / "iterations.json").read_text(encoding="utf-8")), [])

    def test_prepare_repair_candidate_creates_baseline_and_candidate_workspace(self) -> None:
        prepare = load_module(
            "03_repair_target_agent_loop/05_fix_target/scripts/prepare_repair_agent_loop.py",
            "prepare_repair_agent_loop",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "target"
            child = package / "child"
            child.mkdir(parents=True)
            (package / "workflow.lgwf").write_text("WORKFLOW target;\n", encoding="utf-8")
            (child / "script.py").write_text("print('ok')\n", encoding="utf-8")
            lgwf = root / ".lgwf"
            lgwf.mkdir()
            workspace = prepare.prepare_candidate_workspace(
                lgwf,
                {
                    "target_package_root": str(package),
                    "target_workflow_lgwf": str(package / "workflow.lgwf"),
                },
            )
            baseline = Path(workspace["baseline_package_root"])
            candidate = Path(workspace["candidate_package_root"])
            self.assertTrue((baseline / "workflow.lgwf").exists())
            self.assertTrue((candidate / "workflow.lgwf").exists())
            self.assertEqual(workspace["candidate_workflow_lgwf"], (candidate / "workflow.lgwf").as_posix())
            self.assertTrue((lgwf / "target_repair" / "current" / "workspace.json").exists())

    def test_prepare_repair_candidate_rejects_workflow_outside_target_package(self) -> None:
        prepare = load_module(
            "03_repair_target_agent_loop/05_fix_target/scripts/prepare_repair_agent_loop.py",
            "prepare_repair_agent_loop_outside",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = root / "target"
            package.mkdir()
            workflow = root / "other" / "workflow.lgwf"
            workflow.parent.mkdir()
            workflow.write_text("WORKFLOW other;\n", encoding="utf-8")
            lgwf = root / ".lgwf"
            lgwf.mkdir()
            with self.assertRaisesRegex(ValueError, "inside target_package_root"):
                prepare.prepare_candidate_workspace(
                    lgwf,
                    {
                        "target_package_root": str(package),
                        "target_workflow_lgwf": str(workflow),
                    },
                )

    def test_audit_repair_changes_compares_candidate_against_baseline(self) -> None:
        audit = load_module("03_repair_target_agent_loop/05_fix_target/scripts/audit_repair_changes.py", "audit_candidate")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "baseline"
            candidate = root / "candidate"
            baseline.mkdir()
            candidate.mkdir()
            (baseline / "allowed.py").write_text("print('old')\n", encoding="utf-8")
            (candidate / "allowed.py").write_text("print('new')\n", encoding="utf-8")
            (candidate / "extra.py").write_text("print('extra')\n", encoding="utf-8")
            result = audit.audit_candidate_changes(
                baseline,
                candidate,
                {"files_to_modify": ["allowed.py"]},
            )
        self.assertFalse(result["passed"])
        self.assertEqual(result["changed_files"], ["allowed.py", "extra.py"])
        self.assertEqual(result["planned_changes"], ["allowed.py"])
        self.assertEqual(result["unexpected_changes"], ["extra.py"])

    def test_validate_repair_prefers_candidate_workspace_paths(self) -> None:
        validate = load_module("03_repair_target_agent_loop/05_fix_target/scripts/validate_repair.py", "validate_candidate")

        @dataclass
        class Result:
            returncode: int
            stdout: str = ""
            stderr: str = ""

        calls: list[list[str]] = []

        def fake_run(args: list[str], *, timeout: int = 120):
            calls.append(args)
            return Result(0, "{}")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            real = root / "real"
            candidate = root / "candidate"
            real.mkdir()
            candidate.mkdir()
            (real / "workflow.lgwf").write_text("WORKFLOW real;\n", encoding="utf-8")
            candidate_workflow = candidate / "workflow.lgwf"
            candidate_workflow.write_text("WORKFLOW candidate;\n", encoding="utf-8")
            result = validate.validate_target_repair(
                {
                    "target_workflow_lgwf": str(real / "workflow.lgwf"),
                    "target_package_root": str(real),
                },
                workspace={
                    "candidate_workflow_lgwf": str(candidate_workflow),
                    "candidate_package_root": str(candidate),
                },
                run_lgwf_func=fake_run,
                compileall_func=lambda path: Result(0, ""),
            )
        self.assertTrue(result["passed"])
        self.assertEqual(calls[0], ["audit", str(candidate_workflow)])
        self.assertEqual(calls[1], ["compile", str(candidate_workflow)])

    def test_promote_repair_candidate_copies_candidate_changes_to_target(self) -> None:
        promote = load_module(
            "03_repair_target_agent_loop/05_fix_target/scripts/promote_repair_candidate.py",
            "promote_repair_candidate",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            candidate = root / "candidate"
            target.mkdir()
            candidate.mkdir()
            (target / "keep.py").write_text("old\n", encoding="utf-8")
            (target / "remove.py").write_text("remove\n", encoding="utf-8")
            (candidate / "keep.py").write_text("new\n", encoding="utf-8")
            result = promote.promote_candidate_changes(
                candidate,
                target,
                {"passed": True, "changed_files": ["keep.py", "remove.py"]},
            )
            self.assertEqual((target / "keep.py").read_text(encoding="utf-8"), "new\n")
            self.assertFalse((target / "remove.py").exists())
            self.assertEqual(result["promoted_files"], ["keep.py", "remove.py"])
            self.assertEqual(result["target_dirs"], [str(target.resolve())])

    def test_promote_repair_candidate_requires_passed_change_audit(self) -> None:
        promote = load_module(
            "03_repair_target_agent_loop/05_fix_target/scripts/promote_repair_candidate.py",
            "promote_repair_candidate_guard",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "target"
            candidate = root / "candidate"
            target.mkdir()
            candidate.mkdir()
            (target / "keep.py").write_text("old\n", encoding="utf-8")
            (candidate / "keep.py").write_text("new\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "change_audit.passed"):
                promote.promote_candidate_changes(
                    candidate,
                    target,
                    {"passed": False, "changed_files": ["keep.py"], "unexpected_changes": []},
                )
            self.assertEqual((target / "keep.py").read_text(encoding="utf-8"), "old\n")

    def test_target_repair_loop_archives_current_by_iteration(self) -> None:
        loop = load_module("shared/target_repair_loop.py", "target_loop_archive")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / ".lgwf"
            loop.start_iteration(root, {"current_attempt": 1, "max_attempts": 5})
            loop.write_current_artifact(root, "observation", {"status": "failed"})
            first = loop.archive_current_iteration(root, outcome="rerun")
            self.assertEqual(first["iteration"], 1)
            self.assertTrue((root / "target_repair" / "iterations" / "001" / "observation.json").exists())

            loop.start_iteration(root, {"current_attempt": 2, "max_attempts": 5})
            loop.write_current_artifact(root, "observation", {"status": "succeeded"})
            second = loop.archive_current_iteration(root, outcome="finish_success")
            self.assertEqual(second["iteration"], 2)
            self.assertTrue((root / "target_repair" / "iterations" / "002" / "observation.json").exists())
            iterations = json.loads((root / "target_repair" / "iterations.json").read_text(encoding="utf-8"))
            self.assertEqual([item["iteration"] for item in iterations], [1, 2])

    def test_route_after_plan_returns_structured_block_decision(self) -> None:
        decide = load_module("03_repair_target_agent_loop/05_fix_target/scripts/decide_repair_loop.py", "repair_loop_decision")
        decision = decide.choose_decision({"status": "blocked", "blocked_reason": "not enough evidence"}, {"passed": False})
        self.assertEqual(decision["category"], "block")
        self.assertEqual(decision["stop_reason"], "plan_blocked")

    def test_decide_repair_loop_returns_retry_and_finish_decisions(self) -> None:
        decide = load_module("03_repair_target_agent_loop/05_fix_target/scripts/decide_repair_loop.py", "repair_loop_retry")
        retry = decide.choose_decision({"status": "ready"}, {"passed": False, "issues": [{"name": "audit"}]})
        self.assertEqual(retry["category"], "retry")
        self.assertEqual(retry["stop_reason"], "verification_failed")

        finish = decide.choose_decision({"status": "ready"}, {"passed": True, "checks": []})
        self.assertEqual(finish["category"], "finish")
        self.assertEqual(finish["stop_reason"], "repair_candidate_ready")

    def test_decide_repair_loop_retries_when_semantic_review_needed(self) -> None:
        decide = load_module("03_repair_target_agent_loop/05_fix_target/scripts/decide_repair_loop.py", "repair_loop_semantic")
        decision = decide.choose_decision(
            {"status": "ready"},
            {
                "passed": True,
                "semantic_review_needed": True,
                "semantic_risks": [{"name": "missing_change_details"}],
            },
        )
        self.assertEqual(decision["category"], "retry")
        self.assertEqual(decision["stop_reason"], "semantic_review_needed")
        self.assertEqual(decision["evidence"][0]["name"], "missing_change_details")

    def test_route_after_verification_sends_only_semantic_passes_to_review(self) -> None:
        route = load_module("03_repair_target_agent_loop/05_fix_target/scripts/route_after_verification.py", "route_after_verification")
        self.assertEqual(route.choose_route({"passed": True, "semantic_review_needed": True}), "review")
        self.assertEqual(route.choose_route({"passed": True, "semantic_review_needed": False}), "finish")
        self.assertEqual(route.choose_route({"passed": False, "semantic_review_needed": True}), "finish")

    def test_finalize_repair_candidate_review_clears_or_preserves_semantic_risk(self) -> None:
        finalize = load_module(
            "03_repair_target_agent_loop/05_fix_target/scripts/finalize_repair_candidate_review.py",
            "finalize_review",
        )
        passed = finalize.finalize_verification(
            {"passed": True, "semantic_review_needed": True, "semantic_risks": [{"name": "missing_change_details"}]},
            {"status": "pass", "semantic_issues": [], "evidence": [{"source": "apply.json"}]},
        )
        self.assertFalse(passed["semantic_review_needed"])
        self.assertEqual(passed["semantic_risks"], [])

        needs_retry = finalize.finalize_verification(
            {"passed": True, "semantic_review_needed": True, "semantic_risks": [{"name": "missing_change_details"}]},
            {
                "status": "needs_retry",
                "semantic_issues": [{"name": "missing_change_details"}],
                "next_agent_action": "补齐 change_details",
            },
        )
        self.assertTrue(needs_retry["semantic_review_needed"])
        self.assertEqual(needs_retry["semantic_risks"][0]["name"], "missing_change_details")
        self.assertIn("补齐 change_details", needs_retry["retry_hints"])

        not_required = finalize.finalize_verification(
            {"passed": True, "semantic_review_needed": False, "semantic_risks": []},
            {"status": "needs_retry", "semantic_issues": [{"name": "stale_review"}]},
        )
        self.assertEqual(not_required["semantic_review"]["status"], "not_required")
        self.assertFalse(not_required["semantic_review_needed"])

        missing = finalize.finalize_verification(
            {"passed": True, "semantic_review_needed": True, "semantic_risks": [{"name": "missing_change_details"}]},
            {},
        )
        self.assertTrue(missing["semantic_review_needed"])
        self.assertEqual(missing["semantic_review"]["status"], "missing")
        self.assertEqual(missing["semantic_risks"][0]["name"], "semantic_review_missing")

    def test_verify_candidate_requires_ready_plan_and_applied_result(self) -> None:
        verify = load_module("03_repair_target_agent_loop/05_fix_target/scripts/verify_repair_candidate.py", "verify_candidate_checks")
        verify.audit_candidate_changes = lambda baseline, candidate, plan: {"passed": True, "unexpected_changes": []}
        verify.validate_target_repair = lambda target, workspace=None: {"passed": True, "issues": [], "commands": []}
        result = verify.verify_candidate({}, {}, {"status": "blocked"}, {"status": "blocked"})
        self.assertFalse(result["passed"])
        self.assertEqual(result["checks"][0]["name"], "plan_ready")
        self.assertIn("retry_hints", result)
        self.assertIn("重新生成修复计划", result["retry_hints"][0])
        self.assertEqual(result["unexpected_changes"], [])
        self.assertEqual(result["validation_failures"], [])

    def test_verify_candidate_exports_unexpected_changes_and_validation_failures(self) -> None:
        verify = load_module("03_repair_target_agent_loop/05_fix_target/scripts/verify_repair_candidate.py", "verify_candidate_failures")
        verify.audit_candidate_changes = lambda baseline, candidate, plan: {
            "passed": False,
            "unexpected_changes": ["extra.py"],
            "issues": [],
        }
        verify.validate_target_repair = lambda target, workspace=None: {
            "passed": False,
            "issues": [{"check": "audit", "stderr": "bad dsl"}],
            "commands": [["audit", "workflow.lgwf"]],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "baseline"
            candidate = root / "candidate"
            baseline.mkdir()
            candidate.mkdir()
            result = verify.verify_candidate(
                {},
                {"baseline_package_root": str(baseline), "candidate_package_root": str(candidate)},
                {"status": "ready", "files_to_modify": ["workflow.lgwf"]},
                {"status": "applied", "changed_files": ["workflow.lgwf"]},
            )
        self.assertFalse(result["passed"])
        self.assertEqual(result["unexpected_changes"], ["extra.py"])
        self.assertEqual(result["validation_failures"][0]["check"], "audit")
        self.assertTrue(any("收敛修改范围" in hint for hint in result["retry_hints"]))
        self.assertTrue(any("静态校验失败" in hint for hint in result["retry_hints"]))

    def test_verify_candidate_flags_semantic_evidence_gaps_after_static_pass(self) -> None:
        verify = load_module("03_repair_target_agent_loop/05_fix_target/scripts/verify_repair_candidate.py", "verify_candidate_semantic")
        verify.audit_candidate_changes = lambda baseline, candidate, plan: {
            "passed": True,
            "changed_files": ["workflow.lgwf"],
            "planned_changes": ["workflow.lgwf"],
            "unexpected_changes": [],
            "missing_planned_changes": [],
        }
        verify.validate_target_repair = lambda target, workspace=None: {"passed": True, "issues": [], "commands": [["audit", "workflow.lgwf"]]}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            baseline = root / "baseline"
            candidate = root / "candidate"
            baseline.mkdir()
            candidate.mkdir()
            result = verify.verify_candidate(
                {},
                {"baseline_package_root": str(baseline), "candidate_package_root": str(candidate)},
                {"status": "ready", "files_to_modify": ["workflow.lgwf"]},
                {"status": "applied", "changed_files": ["workflow.lgwf"]},
            )
        self.assertTrue(result["passed"])
        self.assertTrue(result["semantic_review_needed"])
        self.assertIn("missing_root_cause_explanation", {risk["name"] for risk in result["semantic_risks"]})
        self.assertIn("missing_change_details", {risk["name"] for risk in result["semantic_risks"]})

    def test_observe_repair_context_builds_structured_signals(self) -> None:
        observe = load_module("03_repair_target_agent_loop/05_fix_target/scripts/observe_repair_context.py", "observe_repair_context_structured")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / ".lgwf"
            current = root / "target_repair" / "current"
            current.mkdir(parents=True)
            (current / "observation.json").write_text(
                json.dumps(
                    {
                        "status": "needs_repair",
                        "phase": "contract_drift",
                        "failure_class": "contract_drift",
                        "issues": [{"phase": "contract_drift", "error": "missing report"}],
                        "contract_audit": {
                            "issues": [{"phase": "output_contract", "error": "report missing"}],
                            "stale_expectations": [{"id": "stock_2"}],
                        },
                        "run_health": {"codex_stream_disconnects": 1, "data_fallback": False},
                    }
                ),
                encoding="utf-8",
            )
            (current / "workspace.json").write_text(
                json.dumps({"candidate_package_root": str(current / "workspace" / "candidate"), "target_dirs": ["candidate"]}),
                encoding="utf-8",
            )
            (current / "verification.json").write_text(
                json.dumps(
                    {
                        "passed": True,
                        "failed_checks": [{"name": "change_audit"}],
                        "retry_hints": ["收敛修改范围"],
                        "unexpected_changes": ["extra.py"],
                        "validation_failures": [{"check": "audit"}],
                        "semantic_review_needed": True,
                        "semantic_risks": [{"name": "missing_change_details"}],
                    }
                ),
                encoding="utf-8",
            )
            result = observe.build_observation(root)
        self.assertEqual(result["failure_signals"][0]["field"], "status")
        self.assertEqual(result["contract_signals"][0]["source"], "contract_audit.issues")
        self.assertEqual(result["run_health_signals"][0]["field"], "codex_stream_disconnects")
        previous_verification = result["previous_iteration_summary"]["verification"]
        self.assertTrue(previous_verification["semantic_review_needed"])
        self.assertEqual(previous_verification["unexpected_changes"], ["extra.py"])
        self.assertEqual(previous_verification["validation_failures"][0]["check"], "audit")
        self.assertIn("candidate_workspace_state", result)

    def test_prepare_requires_target_workflow_lgwf(self) -> None:
        prepare = load_module("01_prepare_target/scripts/prepare_target.py", "prepare_missing")
        with self.assertRaisesRegex(ValueError, "target_workflow_lgwf"):
            prepare.normalize_request({})

    def test_prepare_defaults_max_attempts_to_five(self) -> None:
        prepare = load_module("01_prepare_target/scripts/prepare_target.py", "prepare_default")
        request = prepare.normalize_request({"target_workflow_lgwf": "wf/workflow.lgwf"})
        self.assertEqual(request["max_attempts"], 5)
        self.assertFalse(request["ask_main_agent_for_target_approvals"])

    def test_prepare_accepts_explicit_ask_main_agent_for_target_approvals(self) -> None:
        prepare = load_module("01_prepare_target/scripts/prepare_target.py", "prepare_ask_main_agent")
        enabled = prepare.normalize_request({"target_workflow_lgwf": "wf/workflow.lgwf", "ask_main_agent_for_target_approvals": True})
        disabled = prepare.normalize_request({"target_workflow_lgwf": "wf/workflow.lgwf", "ask_main_agent_for_target_approvals": False})
        self.assertTrue(enabled["ask_main_agent_for_target_approvals"])
        self.assertFalse(disabled["ask_main_agent_for_target_approvals"])

    def test_prepare_builds_target_from_relative_workflow_path(self) -> None:
        prepare = load_module("01_prepare_target/scripts/prepare_target.py", "prepare_target")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wf = root / "target" / "workflow.lgwf"
            wf.parent.mkdir(parents=True)
            wf.write_text("WORKFLOW target;\nENTRY done;\n", encoding="utf-8")
            target = prepare.build_target(
                {
                    "target_workflow_lgwf": "target/workflow.lgwf",
                    "max_attempts": 3,
                    "ask_main_agent_for_target_approvals": True,
                },
                root,
            )
            self.assertEqual(target["target_workflow_lgwf"], str(wf.resolve()))
            self.assertEqual(target["target_package_root"], str(wf.parent.resolve()))
            self.assertEqual(target["target_dirs"], [str(wf.parent.resolve())])
            self.assertEqual(target["max_attempts"], 3)
            self.assertTrue(target["ask_main_agent_for_target_approvals"])

    def test_validate_target_input_requires_json_object(self) -> None:
        validate = load_module("01_prepare_target/scripts/validate_target_workflow_input.py", "validate_input")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / ".lgwf" / "target_workflow_input.json"
            path.parent.mkdir()
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                validate.load_target_input(path)
            path.write_text('{"name":"demo"}', encoding="utf-8")
            self.assertEqual(validate.load_target_input(path), {"name": "demo"})

    def test_route_after_observe_choices(self) -> None:
        route = load_module("03_repair_target_agent_loop/06_route/scripts/route_after_observe.py", "route_choices")
        self.assertEqual(route.choose_route({"last_status": "waiting_approval"}), "finish")
        disabled = route.choose_decision({"last_status": "waiting_approval"})
        self.assertEqual(disabled["category"], "block")
        self.assertEqual(disabled["stop_reason"], "target_waiting_approval_main_agent_confirmation_disabled")
        self.assertEqual(
            route.choose_route({"last_status": "waiting_approval", "ask_main_agent_for_target_approvals": True}),
            "approval",
        )
        self.assertEqual(
            route.choose_decision({"last_status": "waiting_approval"}, {"status": "running"})["route"],
            "observe",
        )
        self.assertEqual(route.choose_route({"last_status": "succeeded"}), "finish")
        self.assertEqual(route.choose_route({"last_status": "needs_repair", "current_attempt": 1, "max_attempts": 5}), "fix")
        self.assertEqual(route.choose_route({"last_status": "running"}), "observe")
        self.assertEqual(route.choose_route({"last_status": "failed", "current_attempt": 1, "max_attempts": 5}), "fix")
        self.assertEqual(route.choose_route({"last_status": "failed", "current_attempt": 5, "max_attempts": 5}), "finish")

    def test_submit_target_approval_normalizes_approve_and_reject(self) -> None:
        submit = load_module(
            "03_repair_target_agent_loop/04_observe_target/scripts/submit_target_approval.py",
            "submit_approval",
        )
        target_value = {"decision": "approve", "comment": "ok", "tuning": {}}
        decision, value, comment = submit.normalize_decision(
            {"decision": "approve", "value": target_value},
            {"context": {"ok": True}},
        )
        self.assertEqual(decision, "approve")
        self.assertEqual(value, target_value)
        self.assertEqual(comment, "user approved")
        decision, value, comment = submit.normalize_decision({"decision": "approve"}, {"context": {"ok": True}})
        self.assertEqual(decision, "approve")
        self.assertEqual(value, {})
        self.assertEqual(comment, "user approved")
        decision, value, comment = submit.normalize_decision({"decision": "reject", "comment": "no"}, {})
        self.assertEqual(decision, "reject")
        self.assertIsNone(value)
        self.assertEqual(comment, "no")
        with self.assertRaisesRegex(ValueError, "approve or reject"):
            submit.normalize_decision({"decision": "maybe"}, {})
        with tempfile.TemporaryDirectory() as temp:
            work_dir = Path(temp)
            human_dir = work_dir / ".lgwf" / "human"
            human_dir.mkdir(parents=True)
            self.assertFalse(submit.has_existing_response(work_dir, "human-1"))
            (human_dir / "human-1.response.json").write_text("{}", encoding="utf-8")
            self.assertTrue(submit.has_existing_response(work_dir, "human-1"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            current = root / "target_repair" / "current"
            current.mkdir(parents=True)
            (current / "observation.json").write_text(
                json.dumps({"status": "running"}),
                encoding="utf-8",
            )
            (current / "approval.json").write_text(
                json.dumps({"status": "waiting_approval", "work_dir": "attempt-001", "request_id": "human-1"}),
                encoding="utf-8",
            )
            approval = submit.load_approval_context(root)
        self.assertEqual(approval["request_id"], "human-1")

    def test_safe_approval_submit_preserves_utf8_payloads(self) -> None:
        safe = load_module("../scripts/safe_approval_submit.py", "safe_approval_submit")
        parser = safe.build_parser()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value_file = root / "value.json"
            value_file.write_text(
                json.dumps({"message": "中文输入", "items": ["不要变成问号"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            args = parser.parse_args(
                [
                    "--work-dir",
                    str(root),
                    "--request-id",
                    "human-1",
                    "--decision",
                    "approve",
                    "--value-file",
                    str(value_file),
                ]
            )
            self.assertEqual(safe.load_json_value(args), {"message": "中文输入", "items": ["不要变成问号"]})

            response = root / "response.json"
            response.write_text(
                json.dumps({"value": {"message": "中文输入", "items": ["不要变成问号"]}}, ensure_ascii=False),
                encoding="utf-8",
            )
            safe.assert_response_preserved_value(response, {"message": "中文输入", "items": ["不要变成问号"]})

            broken = root / "broken.json"
            broken.write_text(json.dumps({"value": {"message": "????"}}, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unchanged"):
                safe.assert_response_preserved_value(broken, {"message": "中文输入"})

    def test_safe_approval_submit_uses_python_api_for_large_payloads(self) -> None:
        safe = load_module("../scripts/safe_approval_submit.py", "safe_approval_submit_large")
        parser = safe.build_parser()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value_file = root / "large-value.json"
            value = {"message": "中文" * 20000, "approval": "approve"}
            value_file.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            response = root / "response.json"
            calls = []

            def fake_submit_main_agent_approval(work_dir, request_id, *, decision, value, comment):
                calls.append(
                    {
                        "work_dir": work_dir,
                        "request_id": request_id,
                        "decision": decision,
                        "value": value,
                        "comment": comment,
                    }
                )
                response.write_text(json.dumps({"value": value}, ensure_ascii=False), encoding="utf-8")
                return {"ok": True, "request_id": request_id, "response_path": str(response)}

            safe.submit_main_agent_approval = fake_submit_main_agent_approval
            args = parser.parse_args(
                [
                    "--work-dir",
                    str(root),
                    "--request-id",
                    "human-large",
                    "--decision",
                    "approve",
                    "--value-file",
                    str(value_file),
                    "--comment",
                    "auto",
                ]
            )
            result = safe.submit(args)
            self.assertTrue(result["ok"])
            self.assertEqual(calls[0]["request_id"], "human-large")
            self.assertEqual(calls[0]["value"], value)

    def test_safe_approval_submit_requires_ascii_for_inline_json(self) -> None:
        safe = load_module("../scripts/safe_approval_submit.py", "safe_approval_submit_ascii")
        parser = safe.build_parser()
        args = parser.parse_args(
            [
                "--work-dir",
                ".",
                "--request-id",
                "human-1",
                "--decision",
                "approve",
                "--value-json-ascii",
                '{"message":"中文"}',
            ]
        )
        with self.assertRaises(UnicodeEncodeError):
            safe.load_json_value(args)

    def test_prepare_input_collection_context_embeds_contract(self) -> None:
        prepare_context = load_module(
            "01_prepare_target/scripts/prepare_input_collection_context.py",
            "prepare_input_context",
        )
        context = prepare_context.build_context(
            {"required_fields": [{"name": "x"}]},
            {"target_workflow_lgwf": "A/workflow.lgwf", "target_package_root": "A"},
        )
        self.assertEqual(context["contract"]["required_fields"][0]["name"], "x")
        self.assertIn("reused", context["instruction"])


if __name__ == "__main__":
    unittest.main()
