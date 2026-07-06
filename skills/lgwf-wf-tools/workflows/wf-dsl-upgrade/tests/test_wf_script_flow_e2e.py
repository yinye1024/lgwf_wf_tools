from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = PACKAGE_ROOT / "wf"

APPROVED_SCRIPTS = {
    "wf/01_collect_targets/scripts/build_target_manifest.py",
    "wf/02_batch_audit/scripts/run_batch_audit.py",
    "wf/03_classify_findings/scripts/classify_findings.py",
    "wf/04_build_upgrade_plan/scripts/build_upgrade_plan.py",
    "wf/05_confirm_upgrade_plan/scripts/prepare_upgrade_plan_approval.py",
    "wf/05_confirm_upgrade_plan/scripts/finalize_upgrade_plan_approval.py",
    "wf/06_apply_upgrade_rules/scripts/apply_upgrade_rules.py",
    "wf/07_batch_verify/scripts/verify_upgraded_workflows.py",
    "wf/08_summarize_upgrade_result/scripts/render_upgrade_summary.py",
}


class WorkflowScriptFlowE2ETests(unittest.TestCase):
    def make_isolated_work_dir(self) -> tempfile.TemporaryDirectory[str]:
        return tempfile.TemporaryDirectory()

    def write_state_json(self, work_dir: Path, relative_path: str, payload: dict) -> Path:
        path = work_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def assert_json_file_fields(
        self,
        work_dir: Path,
        relative_path: str,
        required_fields: list[str],
    ) -> dict:
        path = work_dir / relative_path
        self.assertTrue(path.is_file(), relative_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        for field in required_fields:
            self.assertIn(field, payload, f"{relative_path} missing {field}")
        return payload

    def assert_report_contains_lines(self, work_dir: Path, relative_path: str, lines: list[str]) -> None:
        report = (work_dir / relative_path).read_text(encoding="utf-8")
        for line in lines:
            self.assertIn(line, report)

    def run_script_with_json_stdin(self, relative_script: str, payload: dict) -> dict:
        self.assertIn(relative_script, APPROVED_SCRIPTS)
        script_path = PACKAGE_ROOT / relative_script
        self.assertTrue(script_path.is_file(), relative_script)
        self.assertEqual(WORKFLOW_ROOT, script_path.resolve().parents[2])
        self.assertNotEqual("lgwf.py", script_path.name)
        self.assertNotIn("vendor", script_path.parts)
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            cwd=PACKAGE_ROOT,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertNotIn("--workflow-lgwf", " ".join(completed.args))
        stdout = completed.stdout.strip()
        self.assertTrue(stdout, relative_script)
        return json.loads(stdout)

    def test_case_pipeline_dry_run_reject_summary(self) -> None:
        with self.make_isolated_work_dir() as tmp:
            work_dir = Path(tmp)
            (work_dir / ".lgwf").mkdir(parents=True, exist_ok=True)
            (work_dir / "reports").mkdir(parents=True, exist_ok=True)
            payload = {
                "work_dir": str(work_dir),
                "scope_mode": "registry",
                "targets": [
                    "skills/lgwf-wf-tools/workflows/wf-dsl-upgrade/wf/workflow.lgwf",
                    "skills/lgwf-wf-tools/workflows/wf-dsl-upgrade/wf/05_confirm_upgrade_plan/workflow.lgwf",
                ],
                "max_targets": 8,
                "mode": "dry_run",
            }

            updates = self.run_script_with_json_stdin(
                "wf/01_collect_targets/scripts/build_target_manifest.py",
                payload,
            )
            self.assertIn("lgwf_wf_dsl_upgrade.target_manifest", updates)

            self.run_script_with_json_stdin("wf/02_batch_audit/scripts/run_batch_audit.py", payload)
            self.run_script_with_json_stdin("wf/03_classify_findings/scripts/classify_findings.py", payload)
            self.run_script_with_json_stdin("wf/04_build_upgrade_plan/scripts/build_upgrade_plan.py", payload)
            self.run_script_with_json_stdin(
                "wf/05_confirm_upgrade_plan/scripts/prepare_upgrade_plan_approval.py",
                payload,
            )
            self.run_script_with_json_stdin(
                "wf/05_confirm_upgrade_plan/scripts/finalize_upgrade_plan_approval.py",
                payload,
            )
            self.run_script_with_json_stdin("wf/06_apply_upgrade_rules/scripts/apply_upgrade_rules.py", payload)
            self.run_script_with_json_stdin("wf/07_batch_verify/scripts/verify_upgraded_workflows.py", payload)
            self.run_script_with_json_stdin(
                "wf/08_summarize_upgrade_result/scripts/render_upgrade_summary.py",
                payload,
            )

            target_manifest = self.assert_json_file_fields(
                work_dir,
                ".lgwf/target_manifest.json",
                ["scope_mode", "targets", "max_targets", "authorized"],
            )
            self.assertEqual("registry", target_manifest["scope_mode"])
            self.assertEqual(2, len(target_manifest["targets"]))
            self.assertTrue(target_manifest["authorized"])

            validation = self.assert_json_file_fields(
                work_dir,
                ".lgwf/target_scope_validation.json",
                ["passed", "reasons", "target_count"],
            )
            self.assertTrue(validation["passed"])
            self.assertEqual(2, validation["target_count"])

            batch_result = self.assert_json_file_fields(
                work_dir,
                ".lgwf/batch_audit_result.json",
                ["targets"],
            )
            self.assertEqual(2, len(batch_result["targets"]))

            batch_stats = self.assert_json_file_fields(
                work_dir,
                ".lgwf/batch_audit_stats.json",
                ["target_count", "success_count", "failure_count", "placeholder_count"],
            )
            self.assertEqual(2, batch_stats["target_count"])
            self.assertEqual(2, batch_stats["placeholder_count"])

            classified = self.assert_json_file_fields(
                work_dir,
                ".lgwf/classified_findings.json",
                ["findings"],
            )
            self.assertEqual(2, len(classified["findings"]))
            self.assertTrue(all(item["classification"] == "manual_review" for item in classified["findings"]))

            classification_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/classification_summary.json",
                ["auto_fixable", "manual_review", "unsupported"],
            )
            self.assertEqual(0, classification_summary["auto_fixable"])
            self.assertEqual(2, classification_summary["manual_review"])

            upgrade_plan = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan.json",
                ["items"],
            )
            self.assertEqual([], upgrade_plan["items"])

            plan_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_summary.json",
                ["mode", "plan_count", "empty_plan", "reason"],
            )
            self.assertEqual("dry_run", plan_summary["mode"])
            self.assertEqual(0, plan_summary["plan_count"])
            self.assertTrue(plan_summary["empty_plan"])

            approval_context = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_confirmation_context.json",
                ["mode", "target_count", "classification_summary", "upgrade_plan_summary", "message"],
            )
            self.assertEqual("dry_run", approval_context["mode"])
            self.assertEqual(2, approval_context["target_count"])

            approval = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_approval.json",
                ["decision", "mode", "allow_apply"],
            )
            self.assertEqual("reject", approval["decision"])
            self.assertEqual("dry_run", approval["mode"])
            self.assertFalse(approval["allow_apply"])

            applied = self.assert_json_file_fields(
                work_dir,
                ".lgwf/applied_changes.json",
                ["items", "status"],
            )
            self.assertEqual("skipped", applied["status"])
            self.assertEqual([], applied["items"])

            applied_manifest = self.assert_json_file_fields(
                work_dir,
                ".lgwf/applied_target_manifest.json",
                ["targets", "reason"],
            )
            self.assertEqual([], applied_manifest["targets"])

            post_upgrade_result = self.assert_json_file_fields(
                work_dir,
                ".lgwf/post_upgrade_audit_result.json",
                ["targets", "status"],
            )
            self.assertEqual("skipped", post_upgrade_result["status"])
            self.assertEqual([], post_upgrade_result["targets"])

            diff_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/post_upgrade_diff_summary.json",
                ["modified_count", "resolved_count", "remaining_count", "reason"],
            )
            self.assertEqual(0, diff_summary["modified_count"])
            self.assertEqual(0, diff_summary["resolved_count"])
            self.assertEqual(0, diff_summary["remaining_count"])

            result_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/result_summary.json",
                [
                    "mode",
                    "target_manifest",
                    "classification_summary",
                    "upgrade_plan_summary",
                    "approval",
                    "applied_changes",
                    "post_upgrade_diff_summary",
                    "status",
                ],
            )
            self.assertEqual("dry_run", result_summary["mode"])
            self.assertEqual("reject", result_summary["approval"]["decision"])
            self.assertEqual("draft", result_summary["status"])

            self.assert_report_contains_lines(
                work_dir,
                "reports/wf-dsl-upgrade/report.md",
                ["审批结果: reject", "mode: dry_run"],
            )

    def test_case_pipeline_accepts_runtime_wrapped_payload_and_wrapped_approval(self) -> None:
        with self.make_isolated_work_dir() as tmp:
            work_dir = Path(tmp)
            (work_dir / ".lgwf").mkdir(parents=True, exist_ok=True)
            (work_dir / "reports").mkdir(parents=True, exist_ok=True)
            wrapped_payload = {
                "input": {
                    "payload": {
                        "work_dir": str(work_dir),
                        "scope_mode": "registry",
                        "targets": [
                            "skills/lgwf-wf-tools/workflows/wf-dsl-upgrade/wf/workflow.lgwf",
                            "skills/lgwf-wf-tools/workflows/wf-dsl-upgrade/wf/05_confirm_upgrade_plan/workflow.lgwf",
                        ],
                        "max_targets": 8,
                        "mode": "apply",
                    }
                }
            }

            self.run_script_with_json_stdin(
                "wf/01_collect_targets/scripts/build_target_manifest.py",
                wrapped_payload,
            )
            self.run_script_with_json_stdin("wf/02_batch_audit/scripts/run_batch_audit.py", wrapped_payload)
            self.run_script_with_json_stdin("wf/03_classify_findings/scripts/classify_findings.py", wrapped_payload)
            self.run_script_with_json_stdin("wf/04_build_upgrade_plan/scripts/build_upgrade_plan.py", wrapped_payload)
            self.run_script_with_json_stdin(
                "wf/05_confirm_upgrade_plan/scripts/prepare_upgrade_plan_approval.py",
                wrapped_payload,
            )
            self.write_state_json(
                work_dir,
                ".lgwf/upgrade_plan_approval.json",
                {"value": {"decision": {"value": "approve"}}},
            )
            self.run_script_with_json_stdin(
                "wf/05_confirm_upgrade_plan/scripts/finalize_upgrade_plan_approval.py",
                wrapped_payload,
            )
            self.run_script_with_json_stdin("wf/06_apply_upgrade_rules/scripts/apply_upgrade_rules.py", wrapped_payload)
            self.run_script_with_json_stdin("wf/07_batch_verify/scripts/verify_upgraded_workflows.py", wrapped_payload)
            self.run_script_with_json_stdin(
                "wf/08_summarize_upgrade_result/scripts/render_upgrade_summary.py",
                wrapped_payload,
            )

            target_manifest = self.assert_json_file_fields(
                work_dir,
                ".lgwf/target_manifest.json",
                ["scope_mode", "targets", "max_targets", "authorized"],
            )
            self.assertEqual("registry", target_manifest["scope_mode"])
            self.assertEqual(2, len(target_manifest["targets"]))

            validation = self.assert_json_file_fields(
                work_dir,
                ".lgwf/target_scope_validation.json",
                ["passed", "target_count"],
            )
            self.assertTrue(validation["passed"])
            self.assertEqual(2, validation["target_count"])

            plan_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_summary.json",
                ["mode", "plan_count", "empty_plan"],
            )
            self.assertEqual("apply", plan_summary["mode"])
            self.assertTrue(plan_summary["empty_plan"])

            approval_context = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_confirmation_context.json",
                ["mode", "target_count", "classification_summary", "upgrade_plan_summary", "message"],
            )
            self.assertEqual("apply", approval_context["mode"])
            self.assertEqual(2, approval_context["target_count"])

            approval = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_approval.json",
                ["decision", "mode", "allow_apply"],
            )
            self.assertEqual("approve", approval["decision"])
            self.assertEqual("apply", approval["mode"])
            self.assertTrue(approval["allow_apply"])

            applied = self.assert_json_file_fields(
                work_dir,
                ".lgwf/applied_changes.json",
                ["items", "status"],
            )
            self.assertEqual("placeholder", applied["status"])

            result_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/result_summary.json",
                ["mode", "approval", "status"],
            )
            self.assertEqual("apply", result_summary["mode"])
            self.assertEqual("approve", result_summary["approval"]["decision"])
            self.assertEqual("draft", result_summary["status"])

            self.assert_report_contains_lines(
                work_dir,
                "reports/wf-dsl-upgrade/report.md",
                ["审批结果: approve", "mode: apply"],
            )

    def test_case_finalize_route_fallback_and_apply_authorized_placeholder(self) -> None:
        with self.make_isolated_work_dir() as tmp:
            work_dir = Path(tmp)
            (work_dir / ".lgwf").mkdir(parents=True, exist_ok=True)
            payload = {"work_dir": str(work_dir), "mode": "apply"}
            self.write_state_json(
                work_dir,
                ".lgwf/upgrade_plan.json",
                {
                    "items": [
                        {
                            "target_file": "wf/06_apply_upgrade_rules/workflow.lgwf",
                            "change_summary": "补齐规则占位动作。",
                            "rule_id": "rule-placeholder",
                            "risk": "medium",
                        }
                    ]
                },
            )
            self.write_state_json(
                work_dir,
                ".lgwf/upgrade_plan_approval.json",
                {"route": "approve"},
            )

            self.run_script_with_json_stdin(
                "wf/05_confirm_upgrade_plan/scripts/finalize_upgrade_plan_approval.py",
                payload,
            )
            self.run_script_with_json_stdin("wf/06_apply_upgrade_rules/scripts/apply_upgrade_rules.py", payload)

            approval = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_approval.json",
                ["decision", "mode", "allow_apply"],
            )
            self.assertEqual("approve", approval["decision"])
            self.assertEqual("apply", approval["mode"])
            self.assertTrue(approval["allow_apply"])

            applied = self.assert_json_file_fields(
                work_dir,
                ".lgwf/applied_changes.json",
                ["items", "status"],
            )
            self.assertEqual("placeholder", applied["status"])
            self.assertEqual(1, len(applied["items"]))
            self.assertEqual("wf/06_apply_upgrade_rules/workflow.lgwf", applied["items"][0]["target_file"])
            self.assertEqual("placeholder", applied["items"][0]["status"])
            self.assertIn("change_summary", applied["items"][0])
            self.assertIn("skip_reason", applied["items"][0])

            applied_manifest = self.assert_json_file_fields(
                work_dir,
                ".lgwf/applied_target_manifest.json",
                ["targets"],
            )
            self.assertEqual(
                ["wf/06_apply_upgrade_rules/workflow.lgwf"],
                applied_manifest["targets"],
            )

    def test_case_verify_modified_branch_with_seeded_applied_changes(self) -> None:
        with self.make_isolated_work_dir() as tmp:
            work_dir = Path(tmp)
            (work_dir / ".lgwf").mkdir(parents=True, exist_ok=True)
            payload = {"work_dir": str(work_dir)}
            self.write_state_json(
                work_dir,
                ".lgwf/applied_changes.json",
                {
                    "status": "placeholder",
                    "items": [
                        {
                            "target_file": "wf/04_build_upgrade_plan/workflow.lgwf",
                            "status": "modified",
                            "change_summary": "已种入 modified 分支测试状态。",
                        },
                        {
                            "target_file": "wf/06_apply_upgrade_rules/workflow.lgwf",
                            "status": "placeholder",
                            "change_summary": "非 modified 项不应进入复检目标。",
                        },
                    ],
                },
            )

            self.run_script_with_json_stdin("wf/07_batch_verify/scripts/verify_upgraded_workflows.py", payload)

            post_upgrade_result = self.assert_json_file_fields(
                work_dir,
                ".lgwf/post_upgrade_audit_result.json",
                ["targets", "status"],
            )
            self.assertEqual("placeholder", post_upgrade_result["status"])
            self.assertEqual(1, len(post_upgrade_result["targets"]))
            self.assertEqual("modified", post_upgrade_result["targets"][0]["status"])

            diff_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/post_upgrade_diff_summary.json",
                ["modified_count", "resolved_count", "remaining_count", "reason"],
            )
            self.assertEqual(1, diff_summary["modified_count"])
            self.assertEqual(0, diff_summary["resolved_count"])
            self.assertEqual(0, diff_summary["remaining_count"])

    def test_case_missing_inputs_default_fallbacks(self) -> None:
        with self.make_isolated_work_dir() as tmp:
            work_dir = Path(tmp)
            (work_dir / ".lgwf").mkdir(parents=True, exist_ok=True)

            self.run_script_with_json_stdin(
                "wf/02_batch_audit/scripts/run_batch_audit.py",
                {"work_dir": str(work_dir)},
            )
            self.run_script_with_json_stdin(
                "wf/03_classify_findings/scripts/classify_findings.py",
                {"work_dir": str(work_dir)},
            )
            self.run_script_with_json_stdin(
                "wf/04_build_upgrade_plan/scripts/build_upgrade_plan.py",
                {"work_dir": str(work_dir), "mode": "dry_run"},
            )
            self.run_script_with_json_stdin(
                "wf/05_confirm_upgrade_plan/scripts/finalize_upgrade_plan_approval.py",
                {"work_dir": str(work_dir), "mode": "dry_run"},
            )

            batch_result = self.assert_json_file_fields(
                work_dir,
                ".lgwf/batch_audit_result.json",
                ["targets"],
            )
            self.assertEqual([], batch_result["targets"])

            batch_stats = self.assert_json_file_fields(
                work_dir,
                ".lgwf/batch_audit_stats.json",
                ["target_count", "placeholder_count"],
            )
            self.assertEqual(0, batch_stats["target_count"])
            self.assertEqual(0, batch_stats["placeholder_count"])

            classified = self.assert_json_file_fields(
                work_dir,
                ".lgwf/classified_findings.json",
                ["findings"],
            )
            self.assertEqual([], classified["findings"])

            classification_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/classification_summary.json",
                ["auto_fixable", "manual_review", "unsupported"],
            )
            self.assertEqual(0, classification_summary["manual_review"])

            upgrade_plan = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan.json",
                ["items"],
            )
            self.assertEqual([], upgrade_plan["items"])

            plan_summary = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_summary.json",
                ["mode", "plan_count", "empty_plan", "reason"],
            )
            self.assertEqual("dry_run", plan_summary["mode"])
            self.assertTrue(plan_summary["empty_plan"])

            approval = self.assert_json_file_fields(
                work_dir,
                ".lgwf/upgrade_plan_approval.json",
                ["decision", "mode", "allow_apply"],
            )
            self.assertEqual("reject", approval["decision"])
            self.assertEqual("dry_run", approval["mode"])
            self.assertFalse(approval["allow_apply"])


if __name__ == "__main__":
    unittest.main()
