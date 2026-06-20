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
    def test_repair_loop_uses_diagnose_plan_apply_validate_chain(self) -> None:
        source = (ROOT / "wf" / "03_repair_target_loop" / "workflow.lgwf").read_text(encoding="utf-8")
        for node in (
            "CODEX diagnose_target_failure",
            "CODEX propose_repair_plan",
            "CODEX review_repair_plan",
            "PY route_after_plan",
            "PY capture_repair_snapshot",
            "CODEX apply_repair_plan",
            "PY audit_repair_changes",
            "PY validate_repair",
        ):
            self.assertIn(node, source)
        self.assertIn("WHEN \"fix\" THEN diagnose_target_failure", source)
        self.assertIn(
            "FLOW diagnose_target_failure\n"
            "  THEN propose_repair_plan\n"
            "  THEN review_repair_plan\n"
            "  THEN route_after_plan;",
            source,
        )
        self.assertIn(
            "ROUTE route_after_plan\n"
            "  WHEN \"apply\" THEN capture_repair_snapshot\n"
            "  WHEN \"finish\" THEN finish_self_fix;",
            source,
        )
        self.assertIn(
            "FLOW capture_repair_snapshot\n"
            "  THEN apply_repair_plan\n"
            "  THEN audit_repair_changes\n"
            "  THEN validate_repair\n"
            "  THEN route_after_repair;",
            source,
        )
        self.assertIn(
            "FLOW record_fix_attempt\n"
            "  THEN run_target_workflow;",
            source,
        )
        self.assertIn(
            "ROUTE route_after_repair\n"
            "  WHEN \"rerun\" THEN record_fix_attempt\n"
            "  WHEN \"finish\" THEN finish_self_fix;",
            source,
        )
        self.assertNotIn(
            "validate_repair\n"
            "  THEN record_fix_attempt\n"
            "  THEN run_target_workflow;",
            source,
        )
        self.assertNotIn("CODEX fix_target_workflow", source)
        self.assertEqual(source.count('CONTEXT workspace file ".lgwf/target_run_health.json"'), 4)
        self.assertEqual(source.count('CONTEXT workspace file ".lgwf/target_contract_audit.json"'), 4)

    def test_repair_prompts_cover_contract_drift(self) -> None:
        agents = ROOT / "wf" / "03_repair_target_loop" / "05_fix_target" / "agents"
        for name in (
            "diagnose_target_failure.md",
            "propose_repair_plan.md",
            "review_repair_plan.md",
            "apply_repair_plan.md",
        ):
            source = (agents / name).read_text(encoding="utf-8")
            self.assertIn("target_run_health.json", source)
            self.assertIn("target_contract_audit.json", source)
            self.assertIn("contract_drift", source)
            self.assertIn("output_contract", source)

    def test_root_workflow_wraps_repair_loop_as_subworkflow(self) -> None:
        source = (ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn('STEP prompt_acceptance\n  WORKFLOW "02_prompt_acceptance/workflow.lgwf";', source)
        self.assertIn('STEP repair_target_loop\n  WORKFLOW "03_repair_target_loop/workflow.lgwf";', source)
        self.assertIn('PY summarize_self_fix\n  SCRIPT "04_summarize_self_fix/scripts/summarize_self_fix.py"', source)
        self.assertIn(
            "THEN prepare_target\n"
            "  THEN prompt_acceptance\n"
            "  THEN analyze_target_input_contract",
            source,
        )
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
        observe = load_module("03_repair_target_loop/04_observe_target/scripts/observe_target_run.py", "observe_contract")
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
            review = json.loads((lgwf / "target_failure_review.json").read_text(encoding="utf-8"))
            saved_target = json.loads((lgwf / "self_fix_target.json").read_text(encoding="utf-8"))
        self.assertEqual(result["next_action"], "fix")
        self.assertEqual(saved_target["last_status"], "needs_repair")
        self.assertEqual(review["phase"], "contract_drift")
        self.assertIn("contract_audit", review)
        self.assertIn("contract_drift", {issue["phase"] for issue in review["issues"]})

    def test_observe_finishes_successful_target_with_only_run_health_warnings(self) -> None:
        observe = load_module("03_repair_target_loop/04_observe_target/scripts/observe_target_run.py", "observe_health")
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
            health = json.loads((lgwf / "target_run_health.json").read_text(encoding="utf-8"))
            saved_target = json.loads((lgwf / "self_fix_target.json").read_text(encoding="utf-8"))
        self.assertEqual(result["next_action"], "finish")
        self.assertEqual(saved_target["last_status"], "succeeded")
        self.assertTrue(health["data_fallback"])
        self.assertEqual(health["codex_stream_disconnects"], 1)
        self.assertEqual(health["codex_http_fallbacks"], 1)

    def test_validate_repair_records_failed_static_checks(self) -> None:
        validate = load_module("03_repair_target_loop/05_fix_target/scripts/validate_repair.py", "validate_repair")

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
        route = load_module("03_repair_target_loop/05_fix_target/scripts/route_after_repair.py", "route_after_repair")
        self.assertEqual(route.choose_route({"status": "blocked"}, {"passed": True}), "finish")
        self.assertEqual(route.choose_route({"status": "ready"}, {"passed": False}), "finish")
        self.assertEqual(route.choose_route({"status": "ready"}, {"passed": True}), "rerun")

    def test_route_after_plan_requires_ready_plan_and_passed_review(self) -> None:
        route = load_module("03_repair_target_loop/05_fix_target/scripts/route_after_plan.py", "route_after_plan")
        self.assertEqual(route.choose_route({"status": "blocked"}, {"passed": True, "approved_to_apply": True}), "finish")
        self.assertEqual(route.choose_route({"status": "ready"}, {"passed": False, "approved_to_apply": False}), "finish")
        self.assertEqual(route.choose_route({"status": "ready"}, {"passed": True, "approved_to_apply": True}), "apply")

    def test_audit_repair_changes_rejects_unplanned_file_changes(self) -> None:
        audit = load_module("03_repair_target_loop/05_fix_target/scripts/audit_repair_changes.py", "audit_repair_changes")
        snapshot_mod = load_module(
            "03_repair_target_loop/05_fix_target/scripts/capture_repair_snapshot.py",
            "capture_repair_snapshot",
        )
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp)
            allowed = package / "allowed.py"
            extra = package / "extra.py"
            allowed.write_text("print('old')\n", encoding="utf-8")
            extra.write_text("print('old')\n", encoding="utf-8")
            before = snapshot_mod.capture_snapshot(package)
            allowed.write_text("print('new')\n", encoding="utf-8")
            extra.write_text("print('new')\n", encoding="utf-8")
            result = audit.audit_changes(
                package,
                before,
                {"files_to_modify": ["allowed.py"]},
            )
        self.assertFalse(result["passed"])
        self.assertEqual(result["unexpected_changes"], ["extra.py"])
        self.assertEqual(result["planned_changes"], ["allowed.py"])

    def test_prepare_requires_target_workflow_lgwf(self) -> None:
        prepare = load_module("01_prepare_target/scripts/prepare_target.py", "prepare_missing")
        with self.assertRaisesRegex(ValueError, "target_workflow_lgwf"):
            prepare.normalize_request({})

    def test_prepare_defaults_max_attempts_to_five(self) -> None:
        prepare = load_module("01_prepare_target/scripts/prepare_target.py", "prepare_default")
        request = prepare.normalize_request({"target_workflow_lgwf": "wf/workflow.lgwf"})
        self.assertEqual(request["max_attempts"], 5)

    def test_prepare_builds_target_from_relative_workflow_path(self) -> None:
        prepare = load_module("01_prepare_target/scripts/prepare_target.py", "prepare_target")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wf = root / "target" / "workflow.lgwf"
            wf.parent.mkdir(parents=True)
            wf.write_text("WORKFLOW target;\nENTRY done;\n", encoding="utf-8")
            target = prepare.build_target({"target_workflow_lgwf": "target/workflow.lgwf", "max_attempts": 3}, root)
            self.assertEqual(target["target_workflow_lgwf"], str(wf.resolve()))
            self.assertEqual(target["target_package_root"], str(wf.parent.resolve()))
            self.assertEqual(target["target_dirs"], [str(wf.parent.resolve())])
            self.assertEqual(target["max_attempts"], 3)

    def test_validate_target_input_requires_json_object(self) -> None:
        validate = load_module("02_collect_target_input/scripts/validate_target_workflow_input.py", "validate_input")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / ".lgwf" / "target_workflow_input.json"
            path.parent.mkdir()
            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                validate.load_target_input(path)
            path.write_text('{"name":"demo"}', encoding="utf-8")
            self.assertEqual(validate.load_target_input(path), {"name": "demo"})

    def test_route_after_observe_choices(self) -> None:
        route = load_module("03_repair_target_loop/06_route/scripts/route_after_observe.py", "route_choices")
        self.assertEqual(route.choose_route({"last_status": "waiting_approval"}), "approval")
        self.assertEqual(route.choose_route({"last_status": "succeeded"}), "finish")
        self.assertEqual(route.choose_route({"last_status": "needs_repair", "current_attempt": 1, "max_attempts": 5}), "fix")
        self.assertEqual(route.choose_route({"last_status": "running"}), "observe")
        self.assertEqual(route.choose_route({"last_status": "failed", "current_attempt": 1, "max_attempts": 5}), "fix")
        self.assertEqual(route.choose_route({"last_status": "failed", "current_attempt": 5, "max_attempts": 5}), "finish")

    def test_prompt_acceptance_workflow_uses_step_owned_artifacts_and_react(self) -> None:
        source = (ROOT / "wf" / "02_prompt_acceptance" / "workflow.lgwf").read_text(encoding="utf-8")
        for artifact in (
            ".lgwf/prompt_acceptance/inventory.json",
            ".lgwf/prompt_acceptance/audit.json",
            ".lgwf/prompt_acceptance/fix_selection.json",
            ".lgwf/prompt_acceptance/repair_plan.json",
            ".lgwf/prompt_acceptance/repair_review.json",
            ".lgwf/prompt_acceptance/react_history.json",
        ):
            self.assertIn(artifact, source)
        self.assertIn("CODEX audit_target_prompts", source)
        self.assertIn("APPROVAL select_prompt_fixes", source)
        self.assertIn("REACT repair_target_prompts MAX 3", source)
        self.assertIn("APPROVAL confirm_prompt_acceptance", source)
        self.assertIn('WHEN "fix" THEN repair_target_prompts', source)
        self.assertIn('WHEN "summarize" THEN summarize_prompt_acceptance', source)

    def test_prompt_inventory_discovers_prompt_references_in_nested_workflows(self) -> None:
        inventory_mod = load_module(
            "02_prompt_acceptance/01_inventory/scripts/build_prompt_inventory.py",
            "prompt_inventory",
        )
        with tempfile.TemporaryDirectory() as temp:
            package = Path(temp) / "target"
            nested = package / "child"
            prompt = nested / "agents" / "prompt.md"
            approval = package / "approve.md"
            prompt.parent.mkdir(parents=True)
            prompt.write_text("# Role\nDo work.\n", encoding="utf-8")
            approval.write_text("确认。", encoding="utf-8")
            (package / "workflow.lgwf").write_text(
                'WORKFLOW root;\nAPPROVAL confirm\n  PROMPT_REF "approve.md";\n',
                encoding="utf-8",
            )
            (nested / "workflow.lgwf").write_text(
                'WORKFLOW child;\nREACT demo MAX 3\n'
                '  REASON CODEX\n'
                '    PROMPT "agents/prompt.md"\n',
                encoding="utf-8",
            )
            inventory = inventory_mod.build_prompt_inventory(package / "workflow.lgwf")
        paths = {item["prompt_path"] for item in inventory["prompts"]}
        self.assertEqual(paths, {"approve.md", "child/agents/prompt.md"})
        self.assertTrue(all(item["artifact_root"] == ".lgwf/prompt_acceptance" for item in inventory["prompts"]))

    def test_prompt_fix_selection_supports_all_partial_and_skip(self) -> None:
        selection_mod = load_module(
            "02_prompt_acceptance/03_select_prompt_fixes/scripts/validate_prompt_fix_selection.py",
            "prompt_selection",
        )
        audit = {"issues": [{"id": "p1"}, {"id": "p2"}]}
        self.assertEqual(selection_mod.normalize_selection({"fix_all": True}, audit)["selected_issue_ids"], ["p1", "p2"])
        self.assertEqual(
            selection_mod.normalize_selection({"selected_issue_ids": ["p2", "missing"]}, audit)["selected_issue_ids"],
            ["p2"],
        )
        skipped = selection_mod.normalize_selection({"skip_fix": True, "comment": "later"}, audit)
        self.assertTrue(skipped["skip_fix"])
        self.assertEqual(selection_mod.choose_route(skipped, audit), "summarize")
        self.assertEqual(selection_mod.choose_route({"selected_issue_ids": ["p1"]}, audit), "fix")

    def test_prompt_react_decide_exits_only_when_selected_issues_pass(self) -> None:
        decide_mod = load_module(
            "02_prompt_acceptance/04_repair_prompts/scripts/decide_prompt_fix.py",
            "prompt_decide",
        )
        selection = {"selected_issue_ids": ["p1", "p2"], "skip_fix": False}
        self.assertEqual(
            decide_mod.choose_next(selection, {"passed": True, "remaining_issue_ids": []}),
            "exit",
        )
        self.assertEqual(
            decide_mod.choose_next(selection, {"passed": False, "remaining_issue_ids": ["p2"]}),
            "continue",
        )

    def test_prompt_acceptance_summary_promotes_only_final_root_artifact(self) -> None:
        summary_mod = load_module(
            "02_prompt_acceptance/05_summary/scripts/summarize_prompt_acceptance.py",
            "prompt_summary",
        )
        summary = summary_mod.build_summary(
            inventory={"prompts": [{"prompt_path": "agents/prompt.md"}]},
            audit={"passed": False, "issues": [{"id": "p1", "severity": "high"}]},
            selection={"selected_issue_ids": ["p1"], "skip_fix": False},
            review={"passed": True, "remaining_issue_ids": []},
            history=[{"next": "exit"}],
        )
        self.assertEqual(summary["artifact_root"], ".lgwf/prompt_acceptance")
        self.assertEqual(summary["root_summary_path"], ".lgwf/target_prompt_acceptance_summary.json")
        self.assertEqual(summary["status"], "fixed")
        self.assertEqual(summary["prompt_count"], 1)
        self.assertEqual(summary["selected_issue_ids"], ["p1"])

    def test_submit_target_approval_normalizes_approve_and_reject(self) -> None:
        submit = load_module(
            "03_repair_target_loop/04_observe_target/scripts/submit_target_approval.py",
            "submit_approval",
        )
        decision, value_json, comment = submit.normalize_decision({"decision": "approve"}, {"context": {"ok": True}})
        self.assertEqual(decision, "approve")
        self.assertEqual(json.loads(value_json), {"ok": True})
        self.assertEqual(comment, "user approved")
        decision, value_json, comment = submit.normalize_decision({"decision": "reject", "comment": "no"}, {})
        self.assertEqual(decision, "reject")
        self.assertIsNone(value_json)
        self.assertEqual(comment, "no")
        with self.assertRaisesRegex(ValueError, "approve or reject"):
            submit.normalize_decision({"decision": "maybe"}, {})

    def test_prepare_input_collection_context_embeds_contract(self) -> None:
        prepare_context = load_module(
            "02_collect_target_input/scripts/prepare_input_collection_context.py",
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
