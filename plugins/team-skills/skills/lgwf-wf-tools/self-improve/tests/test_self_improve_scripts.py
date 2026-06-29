from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SELF_IMPROVE = ROOT / "self-improve"
COMMANDS_JSON = ROOT / "commands.json"


class SelfImproveScriptsTest(unittest.TestCase):
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
        agents_md = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for command in commands:
            self.assertIn(command, skill_md)
            self.assertIn(command, agents_md)

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

    def test_incident_trigger_wording_exists(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("只能建议记录 incident；必须用户确认后才能调用", agents)
        self.assertIn("路由错误", agents)
        self.assertIn("监控 handle 丢失", agents)

    def test_help_command_is_documented_as_read_only(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for content in (skill, agents):
            self.assertIn("/lgwf-wf-tools help", content)
            self.assertIn("只展示帮助", content)
            self.assertIn("可用指令", content)
            self.assertIn("不修改文件", content)
            self.assertIn("不派发内部 workflow", content)
            for command in (
                "/lgwf-wf-tools init",
                "/lgwf-wf-tools doctor",
                "/lgwf-wf-tools list",
                "/lgwf-wf-tools self-improve",
            ):
                self.assertIn(command, content)

    def test_self_improve_reminds_user_about_proposal_execution(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        for content in (skill, agents):
            self.assertIn("提醒用户是否查看或执行 proposal", content)
            self.assertIn("不直接执行 proposal", content)
            self.assertIn("执行前必须先展示 review 计划", content)

    def test_ambiguous_modify_goal_requires_proposal_first_gate(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        routing_cases = json.loads(
            (SELF_IMPROVE / "evals" / "baseline-routing-cases.json").read_text(encoding="utf-8")
        )
        cases_by_id = {item["id"]: item for item in routing_cases["cases"]}
        self.assertIn("route-ambiguous-modify-goal-requires-proposal-gate", cases_by_id)
        case = cases_by_id["route-ambiguous-modify-goal-requires-proposal-gate"]

        self.assertIn("ambiguous_modify_goal", agents)
        self.assertIn("禁止改文件", agents)
        self.assertIn("禁止启动任何内部 workflow", agents)
        self.assertIn("目标、发现依据、候选路由、修改范围", agents)
        self.assertIn("除非用户明确说“直接修改”", agents)
        self.assertIn("修复优化", case["input"]["user_request"])
        self.assertIn("apply_patch", case["expected"]["must_not_start"])

    def test_workflow_health_baseline_schema_exists(self) -> None:
        schema = json.loads((SELF_IMPROVE / "workflow-health" / "schema.json").read_text(encoding="utf-8"))
        baseline = json.loads((SELF_IMPROVE / "workflow-health" / "baseline.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["title"], "lgwf-wf-tools workflow health inventory")
        self.assertEqual(
            {item["id"] for item in baseline["workflows"]},
            {"wf-fix", "wf-create", "wf-prompt-fix", "wf-prompt-upgrade", "e2e-test-generator", "plan"},
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
                                    "audit_command": "python audit",
                                    "test_command": "python test",
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
                                    "audit_command": "python audit",
                                    "test_command": "python test",
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


if __name__ == "__main__":
    unittest.main()
