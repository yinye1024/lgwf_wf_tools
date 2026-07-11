from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_SELF_IMPROVE = ROOT / "workflows" / "self-improve"
SELF_IMPROVE = WORKFLOW_SELF_IMPROVE
LEGACY_SELF_IMPROVE = ROOT / "self-improve"
COMMANDS_JSON = ROOT / "commands.json"


class SelfImproveScriptsTest(unittest.TestCase):
    def test_self_improve_primary_entrypoint_lives_under_workflows(self) -> None:
        self.assertTrue((WORKFLOW_SELF_IMPROVE / "AGENTS.md").is_file())
        self.assertTrue((WORKFLOW_SELF_IMPROVE / "scripts" / "self_improve.py").is_file())
        self.assertFalse(LEGACY_SELF_IMPROVE.exists())

        result = subprocess.run(
            [
                sys.executable,
                str(WORKFLOW_SELF_IMPROVE / "scripts" / "validate_manifest.py"),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])

    def test_self_improve_docs_do_not_advertise_legacy_entrypoints(self) -> None:
        docs = [
            ROOT / "docs" / "self-improve.md",
            WORKFLOW_SELF_IMPROVE / "AGENTS.md",
            WORKFLOW_SELF_IMPROVE / "README.md",
            WORKFLOW_SELF_IMPROVE / "loop.md",
        ]
        for path in docs:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("旧路径", text)
                self.assertNotIn("兼容", text)
                self.assertNotIn("python self-improve\\scripts", text)
                self.assertNotIn("python self-improve/scripts", text)

    def test_command_completion_suggests_matching_commands(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "complete_commands.py"),
                "/lgwf-wf-tools d",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        payload = json.loads(result.stdout)
        self.assertEqual(
            [item["command"] for item in payload["matches"]],
            ["/lgwf-wf-tools doctor"],
        )
        self.assertIn("只读检查", payload["matches"][0]["description"])

    def test_command_catalog_stays_documented(self) -> None:
        catalog = json.loads(COMMANDS_JSON.read_text(encoding="utf-8"))
        commands = [item["command"] for item in catalog["commands"]]
        self.assertIn("/lgwf-wf-tools 优化方案", commands)

        skill_md = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for command in commands:
            self.assertIn(command, skill_md)

    def test_self_eval_writes_report_to_requested_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "run_self_evals.py"),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            self.assertTrue(payload["passed"])
            self.assertTrue(Path(payload["json"]).is_file())
            self.assertTrue(Path(payload["md"]).is_file())

    def test_record_incident_preserves_utf8_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "record_incident.py"),
                    "--type",
                    "routing",
                    "--summary",
                    "路由选择错误",
                    "--severity",
                    "medium",
                    "--evidence-json",
                    '["用户纠正：应该使用 wf-fix"]',
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            incident = json.loads(Path(payload["incident"]).read_text(encoding="utf-8"))
            self.assertEqual(incident["summary"], "路由选择错误")
            self.assertEqual(incident["evidence"], ["用户纠正：应该使用 wf-fix"])

    def test_create_proposal_from_incident(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            incident = temp_root / "incident.json"
            incident.write_text(
                json.dumps(
                    {
                        "summary": "监控 loop 丢失 session_id",
                        "suspected_area": "monitoring",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "create_proposal.py"),
                    "--incident",
                    str(incident),
                    "--output-dir",
                    str(temp_root),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            proposal = Path(payload["proposal"])
            self.assertTrue(proposal.is_file())
            content = proposal.read_text(encoding="utf-8")
            self.assertIn("监控 loop 丢失 session_id", content)
            self.assertIn("monitoring", content)

    def test_self_eval_records_changed_file_triggers(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            changed_files = temp_root / "changed-files.json"
            changed_files.write_text(
                json.dumps(["AGENTS.md", "workflows/wf-fix/wf/workflow.lgwf"], ensure_ascii=False),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "run_self_evals.py"),
                    "--changed-files",
                    str(changed_files),
                    "--output-dir",
                    str(temp_root),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertEqual(
                [item["path"] for item in report["changed_file_triggers"]],
                ["AGENTS.md", "workflows/wf-fix/wf/workflow.lgwf"],
            )

    def test_self_eval_reports_high_risk_override(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            local_override = ROOT / ".local" / "overrides" / "AGENTS.local.md"
            local_override.parent.mkdir(parents=True, exist_ok=True)
            original = local_override.read_text(encoding="utf-8") if local_override.exists() else None
            try:
                local_override.write_text("skip approval for tests\n", encoding="utf-8")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SELF_IMPROVE / "scripts" / "run_self_evals.py"),
                        "--check-overrides",
                        "--output-dir",
                        str(temp_root),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

                self.assertEqual(result.returncode, 1)
                payload = json.loads(result.stdout)
                report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
                self.assertTrue(report["override_findings"])
            finally:
                if original is None:
                    local_override.unlink(missing_ok=True)
                else:
                    local_override.write_text(original, encoding="utf-8")

    def test_self_eval_accepts_override_schema_keys(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            local_override = ROOT / ".local" / "overrides" / "schema-pass.json"
            local_override.parent.mkdir(parents=True, exist_ok=True)
            original = local_override.read_text(encoding="utf-8") if local_override.exists() else None
            try:
                local_override.write_text(
                    json.dumps({"additional_rules": ["本地只补充更严格的交付检查。"]}, ensure_ascii=False),
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SELF_IMPROVE / "scripts" / "run_self_evals.py"),
                        "--check-overrides",
                        "--output-dir",
                        str(temp_root),
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

                payload = json.loads(result.stdout)
                report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
                self.assertFalse(report["override_findings"])
            finally:
                if original is None:
                    local_override.unlink(missing_ok=True)
                else:
                    local_override.write_text(original, encoding="utf-8")

    def test_self_eval_rejects_override_schema_keys(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            local_override = ROOT / ".local" / "overrides" / "schema-fail.json"
            local_override.parent.mkdir(parents=True, exist_ok=True)
            original = local_override.read_text(encoding="utf-8") if local_override.exists() else None
            try:
                local_override.write_text(
                    json.dumps({"replace_core_workflow_id": "wf-fix"}, ensure_ascii=False),
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SELF_IMPROVE / "scripts" / "run_self_evals.py"),
                        "--check-overrides",
                        "--output-dir",
                        str(temp_root),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

                self.assertEqual(result.returncode, 1)
                payload = json.loads(result.stdout)
                report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
                self.assertIn("override key is not allowed by schema", report["override_findings"][0]["issue"])
            finally:
                if original is None:
                    local_override.unlink(missing_ok=True)
                else:
                    local_override.write_text(original, encoding="utf-8")

    def test_write_upgrade_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "write_upgrade_report.py"),
                    "--version",
                    "test-version",
                    "--source",
                    "unit-test",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertEqual(report["version"], "test-version")
            self.assertEqual(report["source"], "unit-test")
            self.assertTrue(Path(payload["md"]).is_file())

    def test_collect_changed_files_writes_json_array(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output = Path(raw_dir) / "changed-files.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "collect_changed_files.py"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            self.assertEqual(Path(payload["output"]), output)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertIsInstance(data, list)

    def test_create_eval_case_from_incident(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            incident = temp_root / "incident.json"
            incident.write_text(
                json.dumps(
                    {
                        "id": "incident-1",
                        "type": "routing",
                        "summary": "用户纠正路由选择",
                        "evidence": ["应该选择 wf-fix"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "create_eval_case.py"),
                    "--incident",
                    str(incident),
                    "--output-dir",
                    str(temp_root),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            draft = json.loads(Path(payload["eval_case"]).read_text(encoding="utf-8"))
            self.assertEqual(draft["cases"][0]["review_status"], "draft")
            self.assertEqual(draft["cases"][0]["expected"]["workflow_id"], "wf-fix")

    def test_generate_scorecard(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "generate_scorecard.py"),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            scorecard = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertIn("incident_count", scorecard)
            self.assertTrue(Path(payload["md"]).is_file())

    def test_generate_scorecard_consumes_trace_eval_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            trace_eval = temp_root / "trace-eval.json"
            trace_eval.write_text(
                json.dumps(_failed_trace_eval_report(), ensure_ascii=False),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "generate_scorecard.py"),
                    "--output-dir",
                    str(temp_root),
                    "--trace-eval-report",
                    str(trace_eval),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            scorecard = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertTrue(scorecard["trace_eval"]["available"])
            self.assertFalse(scorecard["trace_eval"]["passed"])
            self.assertEqual(scorecard["trace_eval"]["failed_case_count"], 1)
            self.assertEqual(scorecard["trace_eval"]["failed_check_count"], 3)
            self.assertEqual(scorecard["trace_eval"]["destructive_policy_failure_count"], 1)
            self.assertEqual(scorecard["trace_eval"]["forbidden_permission_failure_count"], 1)
            self.assertEqual(scorecard["trace_eval"]["unexpected_route_failure_count"], 1)
            markdown = Path(payload["md"]).read_text(encoding="utf-8")
            self.assertIn("Trace Eval", markdown)
            self.assertIn("policy.forbidden_destructive", markdown)

    def test_promote_eval_case_requires_approval_and_removes_draft_status(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            draft = temp_root / "draft.json"
            draft.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "cases": [
                            {
                                "id": "draft-routing-case",
                                "category": "routing",
                                "input": {"user_request": "修复 workflow"},
                                "expected": {"workflow_id": "wf-fix"},
                                "review_status": "draft",
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "promote_eval_case.py"),
                    "--draft",
                    str(draft),
                    "--approved-by",
                    "unit-test",
                    "--output-dir",
                    str(temp_root),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            promoted = json.loads(Path(payload["promoted_eval"]).read_text(encoding="utf-8"))
            self.assertEqual(promoted["approved_by"], "unit-test")
            self.assertNotIn("review_status", promoted["cases"][0])

    def test_pre_release_check_runs_aggregate_steps(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "pre_release_check.py"),
                    "--version",
                    "unit-test",
                    "--source",
                    "unit-test",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertTrue(report["passed"])
            self.assertEqual(
                [step["name"] for step in report["steps"]],
                [
                    "doctor",
                    "collect_changed_files",
                    "run_self_evals",
                    "workflow_health",
                    "trace_eval",
                    "generate_scorecard",
                    "write_upgrade_report",
                ],
            )

    def test_pre_release_can_run_workflow_tests_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            baseline = temp_root / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "fast",
                                "expected_role": "test",
                                "audit_command": "python -c \"print('audit')\"",
                                "test_command": "python -c \"print('workflow-test')\"",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "pre_release_check.py"),
                    "--version",
                    "unit-test",
                    "--source",
                    "unit-test",
                    "--output-dir",
                    str(temp_root / "out"),
                    "--run-workflow-tests",
                    "--workflow-tests-baseline",
                    str(baseline),
                    "--workflow-tests-facade-root",
                    str(temp_root),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertEqual(
                [step["name"] for step in report["steps"]],
                [
                    "doctor",
                    "collect_changed_files",
                    "run_self_evals",
                    "workflow_health",
                    "trace_eval",
                    "workflow_tests",
                    "generate_scorecard",
                    "write_upgrade_report",
                ],
            )
            workflow_step = next(step for step in report["steps"] if step["name"] == "workflow_tests")
            self.assertTrue(workflow_step["payload"]["passed"])

    def test_pre_release_fails_when_doctor_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "pre_release_check.py"),
                    "--version",
                    "unit-test",
                    "--source",
                    "unit-test",
                    "--output-dir",
                    str(temp_root),
                    "--doctor-command",
                    "python -c \"import sys; print('{\\\"passed\\\": false}'); sys.exit(1)\"",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertFalse(report["passed"])
            self.assertEqual(report["steps"][0]["name"], "doctor")
            self.assertEqual(report["steps"][0]["returncode"], 1)

    def test_validate_manifest(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SELF_IMPROVE / "scripts" / "validate_manifest.py"),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        payload = json.loads(result.stdout)
        self.assertTrue(payload["passed"])

    def test_unified_self_improve_entrypoint_for_eval(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "self_improve.py"),
                    "eval",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            self.assertTrue(payload["passed"])

    def test_unified_self_improve_entrypoint_for_workflow_health(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "self_improve.py"),
                    "workflow-health",
                    "--workflow-id",
                    "wf-fix",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            self.assertTrue(payload["passed"])

    def test_unified_self_improve_entrypoint_for_trace_eval(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "self_improve.py"),
                    "trace-eval",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            self.assertTrue(payload["passed"])
            self.assertTrue(Path(payload["json"]).is_file())
            self.assertTrue(Path(payload["md"]).is_file())
            self.assertTrue((output_dir / "latest-trace-eval.json").is_file())
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertTrue(Path(report["trace_path"]).is_file())
            self.assertTrue(Path(report["eval_suite_path"]).is_file())
            self.assertIn("failed_checks", report)
            self.assertIn("risk_summary", report)

    def test_workflow_proposal_consumes_trace_eval_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            health = temp_root / "health.json"
            trace_eval = temp_root / "trace-eval.json"
            health.write_text(
                json.dumps(
                    {
                        "workflow_results": [
                            {
                                "id": "wf-fix",
                                "passed": True,
                                "workflow_root": "workflows/wf-fix",
                                "issues": [],
                                "baseline": {
                                    "expected_role": "fix runtime workflow",
                                    "audit_command": "python audit.py",
                                    "test_command": "python test.py",
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            trace_eval.write_text(json.dumps(_failed_trace_eval_report(), ensure_ascii=False), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "create_workflow_improvement_proposal.py"),
                    "--workflow-id",
                    "wf-fix",
                    "--health-report",
                    str(health),
                    "--trace-eval-report",
                    str(trace_eval),
                    "--output-dir",
                    str(temp_root),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            proposal = Path(payload["proposal"]).read_text(encoding="utf-8")
            self.assertIn("Trace Eval Evidence", proposal)
            self.assertIn("policy.forbidden_destructive", proposal)
            self.assertIn("exec.run_shell", proposal)
            self.assertIn("unexpected_route `True`", proposal)

    def test_incident_trigger_wording_exists(self) -> None:
        self_improve = (ROOT / "docs" / "self-improve.md").read_text(encoding="utf-8")
        self.assertIn("只能建议记录 incident；必须用户确认后才能调用", self_improve)
        self.assertIn("路由错误", self_improve)
        self.assertIn("监控 handle 丢失", self_improve)

    def test_help_command_is_documented_as_read_only(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        maintenance = (ROOT / "docs" / "maintenance.md").read_text(encoding="utf-8")
        self.assertIn("/lgwf-wf-tools help", skill)
        self.assertIn("/lgwf-wf-tools init", skill)
        self.assertIn("/lgwf-wf-tools doctor", skill)
        self.assertIn("/lgwf-wf-tools list", skill)
        self.assertIn("docs/maintenance.md", skill)
        for content in (maintenance,):
            self.assertIn("只展示帮助", content)
            self.assertIn("可用指令", content)
            self.assertIn("不修改文件", content)
            self.assertIn("不派发内部 workflow", content)
            for command in (
                "/lgwf-wf-tools init",
                "/lgwf-wf-tools doctor",
                "/lgwf-wf-tools list",
            ):
                self.assertIn(command, content)

    def test_self_improve_reminds_user_about_proposal_execution(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self_improve = (ROOT / "docs" / "self-improve.md").read_text(encoding="utf-8")
        self.assertIn("/lgwf-wf-tools self-improve", skill)
        self.assertIn("/lgwf-wf-tools 自我优化", skill)
        self.assertIn("/lgwf-wf-tools 优化方案", skill)
        self.assertIn("AGENTS.md", skill)
        workflow_agents = (WORKFLOW_SELF_IMPROVE / "AGENTS.md").read_text(encoding="utf-8")
        for content in (self_improve, workflow_agents):
            self.assertIn("提醒用户是否查看或执行 proposal", content)
            self.assertIn("不直接执行 proposal", content)
            self.assertIn("执行前必须先展示 review 计划", content)

    def test_agents_md_only_keeps_routing_scope(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("工作流路由表", agents)
        self.assertIn("前置分流", agents)
        self.assertIn("docs/proposal-gate.md", agents)
        self.assertIn("docs/maintenance.md", agents)
        self.assertIn("显式指令由根目录 `SKILL.md` 做 bootstrap 分发", agents)
        self.assertIn("选择 `target-run`", agents)
        self.assertIn("选择 `self-improve`", agents)
        self.assertIn("workflows/01-share/", agents)
        self.assertNotIn("| 询问可用命令、维护命令含义、发布保护或最小验证 | 不选择 workflow", agents)
        self.assertNotIn("| 询问目标 workflow 直启规则、路径解析或已有 run 处理方式 | 不选择内部 workflow", agents)
        self.assertNotIn("从上表选择一个 workflow id", agents)
        self.assertNotIn("## 可用指令", agents)
        self.assertNotIn("/lgwf-wf-tools init", agents)
        self.assertNotIn("/lgwf-wf-tools doctor", agents)
        self.assertNotIn("/lgwf-wf-tools run <path>", agents)
        self.assertNotIn("ambiguous_modify_goal", agents)
        self.assertNotIn("waiting_human` 不是完成状态", agents)
        self.assertNotIn("发布包不得覆盖或删除 `.local/self-improve/`", agents)
        self.assertNotIn("只能建议记录 incident；必须用户确认后才能调用", agents)

    def test_skill_md_only_declares_entrypoint_and_first_hop(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("bootstrap 指令分发器", skill)
        self.assertIn("读取同目录 [AGENTS.md](AGENTS.md)", skill)
        self.assertIn("显式指令", skill)
        self.assertIn("/lgwf-wf-tools run <path>", skill)
        self.assertIn("/lgwf-wf-tools target-run <path>", skill)
        self.assertIn("/lgwf-wf-tools --target-workflow <path>", skill)
        self.assertIn("路由到 `target-run`", skill)
        self.assertNotIn("docs/target-run.md", skill)
        self.assertNotIn("路由前必须先列出可用 workflow", skill)
        self.assertNotIn("提案门禁", skill)
        self.assertNotIn("监控循环", skill)
        self.assertNotIn("self-improve 路由", skill)

    def test_ambiguous_modify_goal_requires_proposal_first_gate(self) -> None:
        proposal_gate = (ROOT / "docs" / "proposal-gate.md").read_text(encoding="utf-8")
        routing_cases = json.loads(
            (WORKFLOW_SELF_IMPROVE / "evals" / "baseline-routing-cases.json").read_text(encoding="utf-8")
        )
        cases_by_id = {item["id"]: item for item in routing_cases["cases"]}
        self.assertIn("route-ambiguous-modify-goal-requires-proposal-gate", cases_by_id)
        case = cases_by_id["route-ambiguous-modify-goal-requires-proposal-gate"]

        self.assertIn("ambiguous_modify_goal", proposal_gate)
        self.assertIn("禁止改文件", proposal_gate)
        self.assertIn("禁止启动任何内部 workflow", proposal_gate)
        self.assertIn("目标、发现依据、候选路由、修改范围", proposal_gate)
        self.assertIn("除非用户明确说“直接修改”", proposal_gate)
        self.assertIn("修复优化", case["input"]["user_request"])
        self.assertIn("apply_patch", case["expected"]["must_not_start"])

    def test_wf_create_route_must_start_workflow_not_manual_scaffold(self) -> None:
        routing = (ROOT / "docs" / "workflow-routing.md").read_text(encoding="utf-8")
        wf_create_agents = (ROOT / "workflows" / "wf-create" / "AGENTS.md").read_text(encoding="utf-8")
        routing_cases = json.loads(
            (WORKFLOW_SELF_IMPROVE / "evals" / "baseline-routing-cases.json").read_text(encoding="utf-8")
        )
        cases_by_id = {item["id"]: item for item in routing_cases["cases"]}
        self.assertIn("route-new-workflow-creation-must-start-wf-create", cases_by_id)
        case = cases_by_id["route-new-workflow-creation-must-start-wf-create"]

        self.assertEqual(case["expected"]["workflow_id"], "wf-create")
        self.assertIn("apply_patch", case["expected"]["must_not_start"])
        self.assertIn("manual_scaffold", case["expected"]["must_not_start"])
        self.assertIn("禁止主 agent 直接手工创建目标 workflow package", routing)
        self.assertIn("必须启动或继续 `wf-create` run", wf_create_agents)

    def test_workflow_health_baseline_schema_exists(self) -> None:
        schema = json.loads((WORKFLOW_SELF_IMPROVE / "workflow-health" / "schema.json").read_text(encoding="utf-8"))
        baseline = json.loads((WORKFLOW_SELF_IMPROVE / "workflow-health" / "baseline.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "lgwf-wf-tools workflow health inventory")
        self.assertEqual(
            {item["id"] for item in baseline["workflows"]},
            {
                "wf-fix",
                "wf-create",
                "wf-convert",
                "wf-prompt-fix",
                "wf-prompt-upgrade",
                "wf-audit-fix",
                "e2e-test-generator",
                "wf-post-fix",
                "plan",
                "self-improve",
                "target-run",
                "self-improve-seed",
                "skill-packaging",
            },
        )

    def test_check_workflow_health_all_and_single(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            output_dir = Path(raw_dir)
            all_result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "check_workflow_health.py"),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            single_result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "check_workflow_health.py"),
                    "--workflow-id",
                    "wf-fix",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertTrue(json.loads(all_result.stdout)["passed"])
            self.assertTrue(json.loads(single_result.stdout)["passed"])

    def test_check_workflow_health_fails_when_internal_workflow_has_skill(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            fixture = Path(raw_dir)
            workflow_root = fixture / "workflows" / "bad"
            (workflow_root / "tests").mkdir(parents=True)
            (workflow_root / "workflow.lgwf").write_text("WORKFLOW bad;\n", encoding="utf-8")
            (workflow_root / "AGENTS.md").write_text("# Bad\n", encoding="utf-8")
            (workflow_root / "SKILL.md").write_text("# Should not exist\n", encoding="utf-8")
            registry = fixture / "registry.json"
            baseline = fixture / "baseline.json"
            registry.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "bad",
                                "workflow_lgwf": "workflows/bad/workflow.lgwf",
                                "work_dir": "workflows/bad/ws",
                                "agents_md": "workflows/bad/AGENTS.md",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            baseline.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "bad",
                                "expected_role": "test",
                                "audit_command": "python audit",
                                "test_command": "python test",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "check_workflow_health.py"),
                    "--facade-root",
                    str(fixture),
                    "--registry",
                    str(registry),
                    "--baseline",
                    str(baseline),
                    "--output-dir",
                    str(fixture / "out"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertIn("internal workflow must not contain SKILL.md", report["workflow_results"][0]["issues"][0])

    def test_check_workflow_health_reports_missing_semantic_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            fixture = Path(raw_dir)
            workflow_root = fixture / "workflows" / "semantic"
            (workflow_root / "tests").mkdir(parents=True)
            (workflow_root / "workflow.lgwf").write_text("WORKFLOW semantic;\n", encoding="utf-8")
            (workflow_root / "AGENTS.md").write_text("# Semantic\n只有标题。\n", encoding="utf-8")
            registry = fixture / "registry.json"
            baseline = fixture / "baseline.json"
            registry.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "semantic",
                                "workflow_lgwf": "workflows/semantic/workflow.lgwf",
                                "work_dir": "workflows/semantic/ws",
                                "agents_md": "workflows/semantic/AGENTS.md",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            baseline.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "semantic",
                                "expected_role": "test",
                                "audit_command": "python audit",
                                "test_command": "python test",
                                "semantic_requirements": [
                                    {
                                        "id": "approval_boundary",
                                        "description": "说明何时需要 approval",
                                        "any_contains": ["approval", "确认"],
                                    }
                                ],
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "check_workflow_health.py"),
                    "--facade-root",
                    str(fixture),
                    "--registry",
                    str(registry),
                    "--baseline",
                    str(baseline),
                    "--output-dir",
                    str(fixture / "out"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertIn("semantic requirement missing: approval_boundary", report["workflow_results"][0]["issues"])

    def test_check_workflow_health_runs_audit_command_and_fails_on_audit_error(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            fixture = Path(raw_dir)
            workflow_root = fixture / "workflows" / "audit_fail"
            (workflow_root / "tests").mkdir(parents=True)
            (workflow_root / "self-improve" / "scripts").mkdir(parents=True)
            (workflow_root / "workflow.lgwf").write_text("WORKFLOW audit_fail;\n", encoding="utf-8")
            (workflow_root / "AGENTS.md").write_text("# Audit Fail\n", encoding="utf-8")
            (workflow_root / "self-improve" / "manifest.json").write_text(
                json.dumps(
                    {
                        "entrypoint": "scripts/self_improve.py",
                        "local_state_root": ".local/self-improve",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (workflow_root / "self-improve" / "scripts" / "self_improve.py").write_text("", encoding="utf-8")
            (workflow_root / "self-improve" / "scripts" / "check_self_improve.py").write_text("", encoding="utf-8")
            registry = fixture / "registry.json"
            baseline = fixture / "baseline.json"
            registry.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "audit_fail",
                                "kind": "lgwf",
                                "workflow_lgwf": "workflows/audit_fail/workflow.lgwf",
                                "work_dir": "workflows/audit_fail/ws",
                                "agents_md": "workflows/audit_fail/AGENTS.md",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            baseline.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "audit_fail",
                                "expected_role": "test",
                                "audit_command": "python -c \"import sys; print('bad audit'); sys.exit(7)\"",
                                "test_command": "python -c \"print('workflow-test')\"",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "check_workflow_health.py"),
                    "--facade-root",
                    str(fixture),
                    "--registry",
                    str(registry),
                    "--baseline",
                    str(baseline),
                    "--output-dir",
                    str(fixture / "out"),
                    "--audit-timeout-seconds",
                    "5",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            workflow = report["workflow_results"][0]
            self.assertFalse(workflow["audit"]["passed"])
            self.assertEqual(7, workflow["audit"]["returncode"])
            self.assertIn("audit command failed", workflow["issues"])

    def test_check_workflow_health_reports_unregistered_workflow_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            fixture = Path(raw_dir)
            registered = fixture / "workflows" / "registered"
            unregistered = fixture / "workflows" / "wf-audit-fix"
            (registered / "tests").mkdir(parents=True)
            (registered / "self-improve" / "scripts").mkdir(parents=True)
            (unregistered / "wf").mkdir(parents=True)
            (registered / "workflow.lgwf").write_text("WORKFLOW registered;\n", encoding="utf-8")
            (registered / "AGENTS.md").write_text("# Registered\n", encoding="utf-8")
            (registered / "self-improve" / "manifest.json").write_text(
                json.dumps(
                    {
                        "entrypoint": "scripts/self_improve.py",
                        "local_state_root": ".local/self-improve",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (registered / "self-improve" / "scripts" / "self_improve.py").write_text("", encoding="utf-8")
            (registered / "self-improve" / "scripts" / "check_self_improve.py").write_text("", encoding="utf-8")
            (unregistered / "wf" / "workflow.lgwf").write_text("WORKFLOW upgrade;\n", encoding="utf-8")
            (unregistered / "AGENTS.md").write_text("# DSL Upgrade\n", encoding="utf-8")
            registry = fixture / "registry.json"
            baseline = fixture / "baseline.json"
            registry.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "registered",
                                "kind": "lgwf",
                                "workflow_lgwf": "workflows/registered/workflow.lgwf",
                                "work_dir": "workflows/registered/ws",
                                "agents_md": "workflows/registered/AGENTS.md",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            baseline.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "registered",
                                "expected_role": "test",
                                "audit_command": "python -c \"print('audit')\"",
                                "test_command": "python -c \"print('workflow-test')\"",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "check_workflow_health.py"),
                    "--facade-root",
                    str(fixture),
                    "--registry",
                    str(registry),
                    "--baseline",
                    str(baseline),
                    "--output-dir",
                    str(fixture / "out"),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertTrue(report["passed"])
            self.assertEqual(
                [
                    {
                        "id": "wf-audit-fix",
                        "workflow_lgwf": "workflows/wf-audit-fix/wf/workflow.lgwf",
                        "agents_md": "workflows/wf-audit-fix/AGENTS.md",
                    }
                ],
                report["unregistered_workflow_candidates"],
            )

    def test_run_workflow_tests_executes_baseline_test_commands(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            baseline = temp_root / "baseline.json"
            baseline.write_text(
                json.dumps(
                    {
                        "workflows": [
                            {
                                "id": "fast",
                                "expected_role": "test",
                                "audit_command": "python -c \"print('audit')\"",
                                "test_command": "python -c \"print('workflow-test')\"",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "run_workflow_tests.py"),
                    "--baseline",
                    str(baseline),
                    "--facade-root",
                    str(temp_root),
                    "--output-dir",
                    str(temp_root / "out"),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            report = json.loads(Path(payload["json"]).read_text(encoding="utf-8"))
            self.assertTrue(report["passed"])
            self.assertEqual(report["workflow_results"][0]["stdout"], "workflow-test")

    def test_create_workflow_improvement_proposal_from_health_report(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            health_report = temp_root / "health.json"
            health_report.write_text(
                json.dumps(
                    {
                        "workflow_results": [
                            {
                                "id": "wf-fix",
                                "passed": False,
                                "issues": ["workflow tests directory missing"],
                                "baseline": {
                                    "expected_role": "运行目标 workflow",
                                "audit_command": "python -c \"print('audit')\"",
                                "test_command": "python -c \"print('workflow-test')\"",
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "create_workflow_improvement_proposal.py"),
                    "--workflow-id",
                    "wf-fix",
                    "--health-report",
                    str(health_report),
                    "--output-dir",
                    str(temp_root),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            payload = json.loads(result.stdout)
            proposal = Path(payload["proposal"])
            content = proposal.read_text(encoding="utf-8")
            self.assertIn("Workflow Improvement Proposal: wf-fix", content)
            self.assertIn("workflow tests directory missing", content)
            self.assertIn("运行目标 workflow", content)

    def test_create_workflow_improvement_proposal_includes_evidence_scope_and_approval(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            temp_root = Path(raw_dir)
            health_report = temp_root / "health.json"
            incident = temp_root / "incident.json"
            eval_report = temp_root / "eval.json"
            changed_files = temp_root / "changed-files.json"
            health_report.write_text(
                json.dumps(
                    {
                        "workflow_results": [
                            {
                                "id": "wf-fix",
                                "passed": False,
                                "issues": ["semantic requirement missing: output_contract"],
                                "workflow_root": "workflows/wf-fix",
                                "baseline": {
                                    "expected_role": "运行目标 workflow",
                                "audit_command": "python -c \"print('audit')\"",
                                "test_command": "python -c \"print('workflow-test')\"",
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            incident.write_text(
                json.dumps({"id": "inc-1", "type": "approval", "summary": "approval 说明不清"}, ensure_ascii=False),
                encoding="utf-8",
            )
            eval_report.write_text(
                json.dumps({"case_results": [{"id": "case-1", "passed": False, "issues": ["missing wording"]}]}, ensure_ascii=False),
                encoding="utf-8",
            )
            changed_files.write_text(json.dumps(["workflows/wf-fix/AGENTS.md"], ensure_ascii=False), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "create_workflow_improvement_proposal.py"),
                    "--workflow-id",
                    "wf-fix",
                    "--health-report",
                    str(health_report),
                    "--incident",
                    str(incident),
                    "--eval-report",
                    str(eval_report),
                    "--changed-files",
                    str(changed_files),
                    "--output-dir",
                    str(temp_root),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            content = Path(json.loads(result.stdout)["proposal"]).read_text(encoding="utf-8")
            self.assertIn("## 问题证据", content)
            self.assertIn("## 影响范围", content)
            self.assertIn("## 推荐修改文件", content)
            self.assertIn("## 验收命令", content)
            self.assertIn("## 是否需要用户 approval", content)
            self.assertIn("case-1", content)
            self.assertIn("workflows/wf-fix/AGENTS.md", content)

    def test_generate_scorecard_reports_recent_trends(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            local_root = Path(raw_dir) / "self-improve"
            (local_root / "incidents").mkdir(parents=True)
            (local_root / "reports").mkdir(parents=True)
            (local_root / "incidents" / "1.json").write_text(
                json.dumps({"type": "routing", "summary": "wf-fix 路由错误"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (local_root / "incidents" / "2.json").write_text(
                json.dumps({"type": "approval", "summary": "wf-fix approval 卡住"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (local_root / "reports" / "latest-self-eval.json").write_text(
                json.dumps(
                    {
                        "passed": False,
                        "case_results": [
                            {"id": "r1", "category": "routing", "passed": False, "expected": {"workflow_id": "wf-fix"}},
                            {"id": "a1", "category": "approval", "passed": False, "expected": {"workflow_id": "wf-fix"}},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SELF_IMPROVE / "scripts" / "generate_scorecard.py"),
                    "--local-root",
                    str(local_root),
                    "--output-dir",
                    str(Path(raw_dir) / "out"),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            scorecard = json.loads(Path(json.loads(result.stdout)["json"]).read_text(encoding="utf-8"))
            self.assertEqual(scorecard["recent_incident_type_counts"]["routing"], 1)
            self.assertEqual(scorecard["repeated_failed_workflows"]["wf-fix"], 2)
            self.assertEqual(scorecard["routing_misroute_count"], 1)
            self.assertEqual(scorecard["approval_blocker_count"], 1)

    def test_local_state_is_gitignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".local/", gitignore)


def _failed_trace_eval_report() -> dict[str, object]:
    return {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "passed": False,
        "run_id": "run-001",
        "trace_path": ".lgwf/runs/run-001/trace.json",
        "eval_suite_path": ".lgwf/runs/run-001/eval-suite.json",
        "cases_dir": "workflows/self-improve/trace-eval/golden_cases",
        "failed_cases": [
            {
                "case_id": "runtime_trace_contract",
                "description": "runtime contract failed",
                "kind": "runtime_contract",
            }
        ],
        "failed_checks": [
            {
                "case_id": "runtime_trace_contract",
                "check_name": "policy.forbidden_destructive",
                "message": "destructive capabilities used",
                "evidence": [{"node_id": "run_shell", "capability": "exec.run_shell"}],
                "node_id": "run_shell",
                "capability": "exec.run_shell",
                "route": None,
                "client_call_id": None,
                "involves_destructive": True,
                "involves_forbidden_permission": False,
                "involves_unexpected_route": False,
            },
            {
                "case_id": "runtime_trace_contract",
                "check_name": "policy.forbidden_permissions",
                "message": "forbidden permissions used",
                "evidence": [{"node_id": "run_shell", "capability": "exec.run_shell"}],
                "node_id": "run_shell",
                "capability": "exec.run_shell",
                "route": None,
                "client_call_id": None,
                "involves_destructive": False,
                "involves_forbidden_permission": True,
                "involves_unexpected_route": False,
            },
            {
                "case_id": "runtime_trace_contract",
                "check_name": "trajectory.forbidden_routes",
                "message": "forbidden route used",
                "evidence": [{"source_node": "decide", "route_key": "fail", "target_node": "failed"}],
                "node_id": "decide",
                "capability": None,
                "route": "fail",
                "client_call_id": "decide:check",
                "involves_destructive": False,
                "involves_forbidden_permission": False,
                "involves_unexpected_route": True,
            },
        ],
        "risk_summary": {
            "destructive_policy_failure_count": 1,
            "forbidden_permission_failure_count": 1,
            "unexpected_route_failure_count": 1,
        },
    }


if __name__ == "__main__":
    unittest.main()
