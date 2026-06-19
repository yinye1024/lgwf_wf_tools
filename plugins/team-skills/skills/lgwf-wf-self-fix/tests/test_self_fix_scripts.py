from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
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

    def test_root_workflow_wraps_repair_loop_as_subworkflow(self) -> None:
        source = (ROOT / "wf" / "workflow.lgwf").read_text(encoding="utf-8")
        self.assertIn('STEP repair_target_loop\n  WORKFLOW "03_repair_target_loop/workflow.lgwf";', source)
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
        self.assertEqual(summary["status"], "success")
        self.assertEqual(summary["duration_seconds"], 450)
        self.assertEqual(summary["token_usage"]["total_tokens"], 1234)
        self.assertEqual(summary["issues_found"][0]["error"], "missing script")
        self.assertEqual(summary["fixes_applied"], ["Moved missing script into workflow package."])
        self.assertEqual(summary["changed_files"], ["wf/workflow.lgwf"])

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
        self.assertEqual(route.choose_route({"last_status": "running"}), "observe")
        self.assertEqual(route.choose_route({"last_status": "failed", "current_attempt": 1, "max_attempts": 5}), "fix")
        self.assertEqual(route.choose_route({"last_status": "failed", "current_attempt": 5, "max_attempts": 5}), "finish")

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
