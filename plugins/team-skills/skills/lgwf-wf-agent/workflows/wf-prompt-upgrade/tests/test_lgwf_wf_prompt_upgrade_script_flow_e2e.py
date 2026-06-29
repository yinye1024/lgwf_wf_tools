from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock


TARGET_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = TARGET_ROOT
WORKFLOW_ROOT = TARGET_ROOT / "wf"
FORBIDDEN_COMMAND_PATTERNS = ("lgwf.py run", "--workflow-lgwf", "codex")


def load_workflow_script_module(script_relative_path: str, module_name: str):
    script_path = WORKFLOW_ROOT / script_relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def isolated_workspace_cwd():
    previous_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        os.chdir(workspace)
        try:
            yield workspace
        finally:
            os.chdir(previous_cwd)


def write_utf8_json_fixture(workspace: Path, relative_path: str, payload: Any) -> Path:
    path = workspace / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _assert_subset(actual: Any, expected: Any) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AssertionError(f"expected dict, got {type(actual)!r}")
        for key, value in expected.items():
            if key not in actual:
                raise AssertionError(f"missing key: {key}")
            _assert_subset(actual[key], value)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list):
            raise AssertionError(f"expected list, got {type(actual)!r}")
        if len(actual) < len(expected):
            raise AssertionError(f"list too short: {len(actual)} < {len(expected)}")
        for index, value in enumerate(expected):
            _assert_subset(actual[index], value)
        return
    if actual != expected:
        raise AssertionError(f"{actual!r} != {expected!r}")


def assert_json_file_matches_subset(path: Path, subset: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    _assert_subset(payload, subset)
    return payload


def make_minimal_target_workflow_package(base_dir: Path) -> tuple[Path, Path]:
    package_root = base_dir / "target-workflow-package"
    design_prompt = package_root / "02_design_upgrade" / "agents" / "act.md"
    confirm_prompt = package_root / "03_confirm_upgrade" / "confirm_prompt_upgrade.md"
    nested_prompt = package_root / "nested" / "agents" / "reason.md"
    design_prompt.parent.mkdir(parents=True, exist_ok=True)
    confirm_prompt.parent.mkdir(parents=True, exist_ok=True)
    nested_prompt.parent.mkdir(parents=True, exist_ok=True)
    design_prompt.write_text("# 设计 act\n", encoding="utf-8")
    confirm_prompt.write_text("请确认升级。\n", encoding="utf-8")
    nested_prompt.write_text("# 嵌套 reason\n", encoding="utf-8")
    (package_root / "workflow.lgwf").write_text(
        "\n".join(
            [
                "WORKFLOW root;",
                "APPROVAL confirm_prompt_upgrade",
                '  PROMPT_REF "03_confirm_upgrade/confirm_prompt_upgrade.md"',
                "REACT design_prompt_upgrade MAX 3",
                "  ACT CODEX",
                '    PROMPT "02_design_upgrade/agents/act.md"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (package_root / "nested" / "workflow.lgwf").write_text(
        "\n".join(
            [
                "WORKFLOW nested;",
                "REACT nested_reason MAX 1",
                "  REASON CODEX",
                '    PROMPT "agents/reason.md"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return package_root, package_root / "workflow.lgwf"


@contextlib.contextmanager
def patch_skill_discovery_env(workspace: Path, *, skill_dir: Path | None):
    env = {
        "HOME": str(workspace / "fake-home"),
        "USERPROFILE": str(workspace / "fake-home"),
        "HOMEDRIVE": "",
        "HOMEPATH": "",
    }
    if skill_dir is not None:
        env["LGWF_CLIENT_ASSIST"] = str(skill_dir)
        env["LGWF_CLIENT_ASSIST_SKILL_DIR"] = str(skill_dir)
        env["LGWF_ALLOW_TEST_CLIENT_ASSIST_ENV"] = "1"
    with mock.patch.dict(os.environ, env, clear=True):
        yield


@contextlib.contextmanager
def forbidden_runtime_guard():
    def normalize_command(args, kwargs) -> str:
        if "args" in kwargs:
            value = kwargs["args"]
        elif args:
            value = args[0]
        else:
            value = ""
        if isinstance(value, (list, tuple)):
            return " ".join(str(item) for item in value)
        return str(value)

    def wrap_callable(original):
        def guarded(*args, **kwargs):
            command_text = normalize_command(args, kwargs)
            if any(pattern in command_text for pattern in FORBIDDEN_COMMAND_PATTERNS):
                raise AssertionError(f"forbidden runtime command: {command_text}")
            return original(*args, **kwargs)

        return guarded

    def guarded_system(command):
        command_text = str(command)
        if any(pattern in command_text for pattern in FORBIDDEN_COMMAND_PATTERNS):
            raise AssertionError(f"forbidden runtime command: {command_text}")
        return 0

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("subprocess.run", side_effect=wrap_callable(subprocess.run)))
        stack.enter_context(mock.patch("subprocess.Popen", side_effect=wrap_callable(subprocess.Popen)))
        stack.enter_context(mock.patch("subprocess.call", side_effect=wrap_callable(subprocess.call)))
        stack.enter_context(mock.patch("subprocess.check_call", side_effect=wrap_callable(subprocess.check_call)))
        stack.enter_context(mock.patch("subprocess.check_output", side_effect=wrap_callable(subprocess.check_output)))
        stack.enter_context(mock.patch("os.system", side_effect=guarded_system))
        yield


def capture_stdout_json(callback) -> tuple[dict[str, Any], str, Exception | None]:
    stdout = io.StringIO()
    captured_error: Exception | None = None
    with contextlib.redirect_stdout(stdout), forbidden_runtime_guard():
        try:
            callback()
        except Exception as exc:  # noqa: BLE001
            captured_error = exc
    text = stdout.getvalue().strip()
    payload = json.loads(text) if text else {}
    return payload, stdout.getvalue(), captured_error


def run_script_main(script_relative_path: str, module_name: str) -> tuple[dict[str, Any], str, Exception | None]:
    module = load_workflow_script_module(script_relative_path, module_name)
    return capture_stdout_json(module.main)


class LgwfWfPromptUpgradeScriptFlowE2ETest(unittest.TestCase):
    maxDiff = None

    def test_case_environment_check_success_writes_artifact(self) -> None:
        with isolated_workspace_cwd() as workspace:
            skill_dir = workspace / "lgwf-client-assist"
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "AGENTS.md").write_text("# fake lgwf-client-assist\n", encoding="utf-8")

            with patch_skill_discovery_env(workspace, skill_dir=skill_dir):
                payload, _, error = run_script_main(
                    "01_prepare_target/scripts/check_lgwf_client_assist.py",
                    "case_environment_check_success_writes_artifact",
                )

            self.assertIsNone(error)
            environment_check = payload["lgwf_wf_prompt_upgrade.environment_check"]
            self.assertTrue(environment_check["passed"])
            self.assertEqual(environment_check["artifact_root"], ".lgwf/prompt_upgrade")
            self.assertTrue(Path(environment_check["skill_md"]).is_file())
            artifact = assert_json_file_matches_subset(
                workspace / ".lgwf" / "prompt_upgrade" / "environment_check.json",
                {
                    "passed": True,
                    "artifact_root": ".lgwf/prompt_upgrade",
                    "skill_dir": str(skill_dir),
                    "skill_md": str(skill_dir / "AGENTS.md"),
                },
            )
            self.assertTrue(artifact["checked"])

    def test_case_environment_check_uses_bundled_client_without_external_skill(self) -> None:
        with isolated_workspace_cwd() as workspace:
            with patch_skill_discovery_env(workspace, skill_dir=None):
                payload, _, error = run_script_main(
                    "01_prepare_target/scripts/check_lgwf_client_assist.py",
                    "case_environment_check_uses_bundled_client_without_external_skill",
                )

            self.assertIsNone(error)
            environment_check = payload["lgwf_wf_prompt_upgrade.environment_check"]
            self.assertTrue(environment_check["passed"])
            artifact = assert_json_file_matches_subset(
                workspace / ".lgwf" / "prompt_upgrade" / "environment_check.json",
                {
                    "passed": True,
                    "artifact_root": ".lgwf/prompt_upgrade",
                },
            )
            self.assertTrue(Path(artifact["skill_md"]).is_file())
            self.assertTrue(artifact["skill_md"].endswith("AGENTS.md"))
            self.assertTrue(artifact["checked"])

    def test_case_inventory_builds_from_persisted_target(self) -> None:
        with isolated_workspace_cwd() as workspace:
            package_root, workflow_lgwf = make_minimal_target_workflow_package(workspace)
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade_target.json",
                {"target_workflow_lgwf": os.path.relpath(workflow_lgwf, workspace)},
            )

            payload, _, error = run_script_main(
                "01_prepare_target/scripts/build_prompt_inventory.py",
                "case_inventory_builds_from_persisted_target",
            )

            self.assertIsNone(error)
            target_payload = payload["lgwf_wf_prompt_upgrade.prompt_upgrade_target"]
            inventory = payload["lgwf_wf_prompt_upgrade.prompt_inventory"]
            self.assertEqual(payload["lgwf_wf_prompt_upgrade.target_dirs"], [str(package_root.resolve())])
            self.assertEqual(target_payload["target_workflow_lgwf"], str(workflow_lgwf.resolve()))
            self.assertEqual(target_payload["target_package_root"], str(package_root.resolve()))
            self.assertEqual(target_payload["target_dirs"], [str(package_root.resolve())])
            rewritten_target = assert_json_file_matches_subset(
                workspace / ".lgwf" / "prompt_upgrade_target.json",
                {
                    "target_workflow_lgwf": str(workflow_lgwf.resolve()),
                    "target_package_root": str(package_root.resolve()),
                    "target_dirs": [str(package_root.resolve())],
                },
            )
            self.assertEqual(rewritten_target["target_dirs"], [str(package_root.resolve())])
            inventory_artifact = assert_json_file_matches_subset(
                workspace / ".lgwf" / "prompt_upgrade" / "inventory.json",
                {
                    "artifact_root": ".lgwf/prompt_upgrade",
                    "target_workflow_lgwf": str(workflow_lgwf.resolve()),
                    "target_package_root": str(package_root.resolve()),
                },
            )
            self.assertTrue(inventory_artifact["prompts"])
            prompt_paths = {item["prompt_path"] for item in inventory_artifact["prompts"]}
            self.assertEqual(
                prompt_paths,
                {
                    "02_design_upgrade/agents/act.md",
                    "03_confirm_upgrade/confirm_prompt_upgrade.md",
                    "nested/agents/reason.md",
                },
            )
            for prompt in inventory["prompts"]:
                self.assertTrue(
                    {"prompt_path", "workflow_path", "ref_kind", "exists", "node_type", "node_id", "artifact_root"}
                    <= set(prompt)
                )

    def test_case_design_decision_continue_when_not_ready(self) -> None:
        with isolated_workspace_cwd() as workspace:
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/proposal.json", {"prompt_upgrades": []})
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/proposal_review.json",
                {"passed": False, "ready_for_confirmation": False, "blocking_issues": ["缺少设计提案"]},
            )

            payload, _, error = run_script_main(
                "02_design_upgrade/scripts/decide_prompt_upgrade_design.py",
                "case_design_decision_continue_when_not_ready",
            )

            self.assertIsNone(error)
            self.assertEqual(payload, {"next": "continue"})
            assert_json_file_matches_subset(
                workspace / ".lgwf" / "prompt_upgrade" / "design_decision.json",
                {"next": "continue"},
            )
            self.assertFalse((workspace / ".lgwf" / "prompt_upgrade" / "confirmation_context.json").exists())
            self.assertFalse((workspace / ".lgwf" / "prompt_upgrade" / "decision.json").exists())

    def test_case_design_exit_then_prepare_confirmation_apply_and_summary_upgraded(self) -> None:
        with isolated_workspace_cwd() as workspace:
            proposal = {
                "summary": "升级 prompt 设计与应用环节。",
                "target_outcome": "让 prompt-upgrade workflow 更稳定。",
                "prompt_upgrades": [
                    {"id": "upgrade_design", "summary": "升级设计 prompt"},
                    {"id": "upgrade_apply", "summary": "升级应用 prompt"},
                ],
                "files_to_modify": [
                    "wf/02_design_upgrade/agents/act.md",
                    "wf/04_apply_upgrade/act_apply_prompt_upgrade/agents/act.md",
                ],
                "risks": ["需要保持审批语义稳定"],
            }
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/proposal.json", proposal)
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/proposal_review.json",
                {"passed": True, "ready_for_confirmation": True, "blocking_issues": []},
            )
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/inventory.json",
                {
                    "prompts": [
                        {"prompt_path": "wf/02_design_upgrade/agents/act.md"},
                        {"prompt_path": "wf/04_apply_upgrade/act_apply_prompt_upgrade/agents/act.md"},
                    ]
                },
            )
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/analysis.json", {"summary": "静态分析通过。"})
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/decision.json", {"approve": True})
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/apply_review.json",
                {"passed": True, "remaining_upgrade_ids": [], "summary": "全部升级已应用。"},
            )
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/react_history.json", [{"event": "before_apply"}])

            design_payload, _, design_error = run_script_main(
                "02_design_upgrade/scripts/decide_prompt_upgrade_design.py",
                "case_design_exit_then_prepare_confirmation_apply_and_summary_upgraded_design",
            )
            self.assertIsNone(design_error)
            self.assertEqual(design_payload, {"next": "exit"})
            assert_json_file_matches_subset(
                workspace / ".lgwf" / "prompt_upgrade" / "design_decision.json",
                {"next": "exit"},
            )

            confirmation_payload, _, confirmation_error = run_script_main(
                "03_confirm_upgrade/scripts/prepare_prompt_upgrade_confirmation.py",
                "case_design_exit_then_prepare_confirmation_apply_and_summary_upgraded_confirmation",
            )
            self.assertIsNone(confirmation_error)
            context = confirmation_payload["lgwf_wf_prompt_upgrade.prompt_upgrade_confirmation_context"]
            self.assertTrue(context["ready_for_confirmation"])
            self.assertEqual(context["upgrade_count"], 2)
            self.assertEqual(context["prompt_count"], 2)
            self.assertEqual(context["analysis_summary"], "静态分析通过。")
            self.assertIn("approve", context["instructions"])

            validate_payload, _, validate_error = run_script_main(
                "03_confirm_upgrade/scripts/validate_prompt_upgrade_decision.py",
                "case_design_exit_then_prepare_confirmation_apply_and_summary_upgraded_validate",
            )
            self.assertIsNone(validate_error)
            normalized_decision = validate_payload["lgwf_wf_prompt_upgrade.prompt_upgrade_decision"]
            self.assertTrue(normalized_decision["approve"])
            self.assertFalse(normalized_decision["reject"])
            self.assertEqual(normalized_decision["approved_upgrade_ids"], ["upgrade_design", "upgrade_apply"])
            assert_json_file_matches_subset(
                workspace / ".lgwf" / "prompt_upgrade" / "decision.json",
                {
                    "approve": True,
                    "reject": False,
                    "approved_upgrade_ids": ["upgrade_design", "upgrade_apply"],
                },
            )

            route_payload, _, route_error = run_script_main(
                "03_confirm_upgrade/scripts/route_after_prompt_upgrade_decision.py",
                "case_design_exit_then_prepare_confirmation_apply_and_summary_upgraded_route",
            )
            self.assertIsNone(route_error)
            self.assertEqual(route_payload["__route__route_after_prompt_upgrade_decision"], "apply")
            self.assertEqual(route_payload["lgwf_wf_prompt_upgrade.prompt_upgrade_route"], "apply")

            apply_payload, _, apply_error = run_script_main(
                "04_apply_upgrade/scripts/decide_prompt_upgrade_apply.py",
                "case_design_exit_then_prepare_confirmation_apply_and_summary_upgraded_apply",
            )
            self.assertIsNone(apply_error)
            self.assertEqual(apply_payload, {"next": "exit"})
            history = json.loads(
                (workspace / ".lgwf" / "prompt_upgrade" / "react_history.json").read_text(encoding="utf-8")
            )
            self.assertEqual(history[-1]["event"], "prompt_upgrade_apply_decided")
            self.assertEqual(history[-1]["next"], "exit")

            summary_payload, _, summary_error = run_script_main(
                "05_summary/scripts/summarize_prompt_upgrade.py",
                "case_design_exit_then_prepare_confirmation_apply_and_summary_upgraded_summary",
            )
            self.assertIsNone(summary_error)
            summary = summary_payload["lgwf_wf_prompt_upgrade.prompt_upgrade_summary"]
            self.assertEqual(summary["status"], "upgraded")
            self.assertEqual(summary["approved_upgrade_ids"], ["upgrade_design", "upgrade_apply"])
            for relative in (".lgwf/prompt_upgrade/summary.json", ".lgwf/target_prompt_upgrade_summary.json"):
                assert_json_file_matches_subset(
                    workspace / relative,
                    {
                        "status": "upgraded",
                        "approved_upgrade_ids": ["upgrade_design", "upgrade_apply"],
                    },
                )

    def test_case_reject_route_to_summary_status_rejected(self) -> None:
        with isolated_workspace_cwd() as workspace:
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/proposal.json",
                {
                    "summary": "暂不升级。",
                    "prompt_upgrades": [{"id": "upgrade_design"}],
                    "files_to_modify": ["wf/02_design_upgrade/agents/act.md"],
                },
            )
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/inventory.json",
                {"prompts": [{"prompt_path": "wf/02_design_upgrade/agents/act.md"}]},
            )
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/decision.json",
                {"reject": True, "comment": "暂不应用"},
            )
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/react_history.json", [])

            validate_payload, _, validate_error = run_script_main(
                "03_confirm_upgrade/scripts/validate_prompt_upgrade_decision.py",
                "case_reject_route_to_summary_status_rejected_validate",
            )
            self.assertIsNone(validate_error)
            normalized_decision = validate_payload["lgwf_wf_prompt_upgrade.prompt_upgrade_decision"]
            self.assertFalse(normalized_decision["approve"])
            self.assertTrue(normalized_decision["reject"])
            self.assertEqual(normalized_decision["approved_upgrade_ids"], [])

            route_payload, _, route_error = run_script_main(
                "03_confirm_upgrade/scripts/route_after_prompt_upgrade_decision.py",
                "case_reject_route_to_summary_status_rejected_route",
            )
            self.assertIsNone(route_error)
            self.assertEqual(route_payload["__route__route_after_prompt_upgrade_decision"], "summarize")

            summary_payload, _, summary_error = run_script_main(
                "05_summary/scripts/summarize_prompt_upgrade.py",
                "case_reject_route_to_summary_status_rejected_summary",
            )
            self.assertIsNone(summary_error)
            self.assertEqual(summary_payload["lgwf_wf_prompt_upgrade.prompt_upgrade_summary"]["status"], "rejected")
            for relative in (".lgwf/prompt_upgrade/summary.json", ".lgwf/target_prompt_upgrade_summary.json"):
                assert_json_file_matches_subset(
                    workspace / relative,
                    {
                        "status": "rejected",
                        "approved_upgrade_ids": [],
                    },
                )

    def test_case_apply_decision_continue_and_summary_needs_attention(self) -> None:
        with isolated_workspace_cwd() as workspace:
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/proposal.json",
                {
                    "summary": "还有未完成的应用动作。",
                    "prompt_upgrades": [{"id": "upgrade_apply"}],
                    "files_to_modify": ["wf/04_apply_upgrade/act_apply_prompt_upgrade/agents/act.md"],
                },
            )
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/inventory.json",
                {"prompts": [{"prompt_path": "wf/04_apply_upgrade/act_apply_prompt_upgrade/agents/act.md"}]},
            )
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/decision.json",
                {"approve": True, "approved_upgrade_ids": ["upgrade_apply"], "reject": False},
            )
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/apply_review.json",
                {
                    "passed": False,
                    "remaining_upgrade_ids": ["upgrade_apply"],
                    "issues": ["仍有阻塞问题"],
                },
            )
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/react_history.json", [])

            apply_payload, _, apply_error = run_script_main(
                "04_apply_upgrade/scripts/decide_prompt_upgrade_apply.py",
                "case_apply_decision_continue_and_summary_needs_attention_apply",
            )
            self.assertIsNone(apply_error)
            self.assertEqual(apply_payload, {"next": "continue"})
            history = json.loads(
                (workspace / ".lgwf" / "prompt_upgrade" / "react_history.json").read_text(encoding="utf-8")
            )
            self.assertEqual(history[-1]["event"], "prompt_upgrade_apply_decided")
            self.assertEqual(history[-1]["next"], "continue")

            summary_payload, _, summary_error = run_script_main(
                "05_summary/scripts/summarize_prompt_upgrade.py",
                "case_apply_decision_continue_and_summary_needs_attention_summary",
            )
            self.assertIsNone(summary_error)
            summary = summary_payload["lgwf_wf_prompt_upgrade.prompt_upgrade_summary"]
            self.assertEqual(summary["status"], "needs_attention")
            self.assertEqual(summary["remaining_upgrade_ids"], ["upgrade_apply"])
            for relative in (".lgwf/prompt_upgrade/summary.json", ".lgwf/target_prompt_upgrade_summary.json"):
                assert_json_file_matches_subset(
                    workspace / relative,
                    {
                        "status": "needs_attention",
                        "remaining_upgrade_ids": ["upgrade_apply"],
                    },
                )

    def test_case_summary_without_upgrades_marks_no_upgrades_proposed(self) -> None:
        with isolated_workspace_cwd() as workspace:
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/inventory.json",
                {
                    "prompts": [
                        {"prompt_path": "wf/02_design_upgrade/agents/act.md"},
                        {"prompt_path": "wf/04_apply_upgrade/act_apply_prompt_upgrade/agents/act.md"},
                    ]
                },
            )
            write_utf8_json_fixture(
                workspace,
                ".lgwf/prompt_upgrade/proposal.json",
                {"prompt_upgrades": [], "files_to_modify": [], "summary": "暂无升级建议。"},
            )
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/decision.json", {})
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/apply_review.json", {})
            write_utf8_json_fixture(workspace, ".lgwf/prompt_upgrade/react_history.json", [])

            summary_payload, _, summary_error = run_script_main(
                "05_summary/scripts/summarize_prompt_upgrade.py",
                "case_summary_without_upgrades_marks_no_upgrades_proposed",
            )
            self.assertIsNone(summary_error)
            summary = summary_payload["lgwf_wf_prompt_upgrade.prompt_upgrade_summary"]
            self.assertEqual(summary["status"], "no_upgrades_proposed")
            self.assertEqual(summary["prompt_count"], 2)
            self.assertEqual(summary["upgrade_count"], 0)
            for relative in (".lgwf/prompt_upgrade/summary.json", ".lgwf/target_prompt_upgrade_summary.json"):
                assert_json_file_matches_subset(
                    workspace / relative,
                    {
                        "status": "no_upgrades_proposed",
                        "prompt_count": 2,
                        "upgrade_count": 0,
                    },
                )


if __name__ == "__main__":
    unittest.main()
