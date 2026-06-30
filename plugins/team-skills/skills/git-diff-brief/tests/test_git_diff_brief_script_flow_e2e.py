from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
import uuid
from pathlib import Path
from unittest import mock


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = PACKAGE_ROOT / "wf"
FORBIDDEN_PATTERNS = ("lgwf.py run", "--workflow-lgwf", "codex")

sys.dont_write_bytecode = True


def load_script_module(relative_path: str) -> types.ModuleType:
    module_path = PACKAGE_ROOT / relative_path
    module_name = f"git_diff_brief_{module_path.stem}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def isolated_workdir_with_lgwf_state() -> Path:
    with tempfile.TemporaryDirectory() as temp_dir:
        workdir = Path(temp_dir)
        (workdir / ".lgwf").mkdir(parents=True, exist_ok=True)
        yield workdir


def write_utf8_json_fixture(workdir: Path, relative_path: str, payload: dict[str, object]) -> Path:
    path = workdir / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


@contextlib.contextmanager
def runtime_guard() -> None:
    def _blocked(*args, **kwargs):
        raise AssertionError(f"脚本级 E2E 禁止启动 runtime 或外部命令: args={args!r}")

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch("subprocess.run", side_effect=_blocked))
        stack.enter_context(mock.patch("subprocess.Popen", side_effect=_blocked))
        stack.enter_context(mock.patch("subprocess.check_call", side_effect=_blocked))
        stack.enter_context(mock.patch("subprocess.check_output", side_effect=_blocked))
        stack.enter_context(mock.patch("os.system", side_effect=_blocked))
        yield


def capture_main_stdout_json(module: types.ModuleType, workdir: Path) -> dict[str, object]:
    buffer = io.StringIO()
    with runtime_guard(), mock.patch("sys.stdout", buffer):
        previous_cwd = Path.cwd()
        os.chdir(workdir)
        try:
            module.main()
        finally:
            os.chdir(previous_cwd)
    return json.loads(buffer.getvalue())


def assert_route_decision_map(
    testcase: unittest.TestCase,
    workflow_relative_path: str,
    node_name: str,
    expected_routes: dict[str, str],
) -> None:
    workflow_text = (PACKAGE_ROOT / workflow_relative_path).read_text(encoding="utf-8")
    marker = f"{node_name}\n"
    marker_index = workflow_text.index(marker)
    section = workflow_text[marker_index:]
    actual_routes: dict[str, str] = {}
    for raw_line in section.splitlines()[1:]:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("WHEN "):
            parts = line.split('"')
            decision = parts[1]
            target = line.rsplit(" ", 1)[-1].rstrip(";")
            actual_routes[decision] = target
            continue
        if actual_routes:
            break
    testcase.assertEqual(expected_routes, actual_routes)


class ScriptFlowE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validate_repo_hint = load_script_module(
            "wf/01_request_scope_alignment/scripts/validate_repo_hint.py"
        )
        cls.prepare_scope_confirmation = load_script_module(
            "wf/01_request_scope_alignment/scripts/prepare_scope_confirmation.py"
        )
        cls.finalize_scope_confirmation = load_script_module(
            "wf/01_request_scope_alignment/scripts/finalize_scope_confirmation.py"
        )
        cls.collect_git_context = load_script_module(
            "wf/02_git_context_collection/scripts/collect_git_context.py"
        )
        cls.derive_validation_suggestions = load_script_module(
            "wf/03_brief_synthesis/scripts/derive_validation_suggestions.py"
        )
        cls.prepare_delivery_review = load_script_module(
            "wf/04_result_review_and_delivery/scripts/prepare_delivery_review.py"
        )
        cls.finalize_brief_result = load_script_module(
            "wf/04_result_review_and_delivery/scripts/finalize_brief_result.py"
        )

    def test_case_scope_validation_normalizes_repo_hint_and_rejects_invalid_inputs(self) -> None:
        self.assertEqual("foo/bar", self.validate_repo_hint.normalize_repo_hint(r"foo\bar"))
        with self.assertRaises(ValueError):
            self.validate_repo_hint.normalize_repo_hint(" ")
        with self.assertRaises(ValueError):
            self.validate_repo_hint.normalize_repo_hint(".lgwf/run")

        result = self.validate_repo_hint.build_scope_validation(
            {
                "repo_hint": r"foo\bar",
                "requested_extensions": ["README", " docs "],
            }
        )
        self.assertEqual("foo/bar", result["normalized_repo_hint"])
        self.assertTrue(result["request_scope_validation"]["needs_confirmation"])
        self.assertEqual(
            "worktree git diff + latest commit",
            result["request_scope_validation"]["baseline_scope"],
        )
        self.assertEqual("revise", result["scope_confirmation_input"]["recommended_decision"])

    def test_case_prepare_scope_confirmation_falls_back_when_capture_missing(self) -> None:
        with isolated_workdir_with_lgwf_state() as workdir:
            result = self.prepare_scope_confirmation.load_capture(
                workdir / ".lgwf/request_scope_capture.json"
            )
            self.assertEqual({}, result["repository_input_context"])
            self.assertEqual({}, result["summary_scope"])
            self.assertTrue(result["scope_confirmation_input"]["needs_confirmation"])
            self.assertIn(
                "缺少 request_scope_capture.json",
                result["scope_confirmation_input"]["open_questions"][0],
            )

            payload = capture_main_stdout_json(self.prepare_scope_confirmation, workdir)
            self.assertEqual({}, payload["git_diff_brief.repository_input_context"])
            self.assertEqual({}, payload["git_diff_brief.summary_scope"])
            self.assertEqual(
                ".lgwf/request_scope_capture.json",
                payload["git_diff_brief.prepare_scope_confirmation_result"]["source_file"],
            )
            self.assertEqual(
                "revise",
                payload["git_diff_brief.scope_confirmation_input"]["recommended_decision"],
            )

    def test_case_scope_approval_routes_and_finalize_contract(self) -> None:
        capture_fixture = {
            "repository_input_context": {"repo_hint": "wf"},
            "summary_scope": {"baseline_scope": "worktree git diff + latest commit"},
            "scope_confirmation_input": {
                "needs_confirmation": False,
                "open_questions": [],
                "recommended_decision": "approve",
            },
        }
        with isolated_workdir_with_lgwf_state() as workdir:
            write_utf8_json_fixture(workdir, ".lgwf/request_scope_capture.json", capture_fixture)
            for decision in ("approve", "revise", "reject"):
                decision_path = write_utf8_json_fixture(
                    workdir,
                    ".lgwf/request_scope_confirmation.json",
                    {"decision": decision},
                )
                persisted = json.loads(decision_path.read_text(encoding="utf-8"))
                self.assertIn(persisted["decision"], {"approve", "revise", "reject"})

            prepared = self.prepare_scope_confirmation.load_capture(
                workdir / ".lgwf/request_scope_capture.json"
            )
            self.assertEqual(
                capture_fixture["repository_input_context"],
                prepared["repository_input_context"],
            )
            self.assertEqual(capture_fixture["summary_scope"], prepared["summary_scope"])
            self.assertEqual(
                capture_fixture["scope_confirmation_input"],
                prepared["scope_confirmation_input"],
            )

            payload = capture_main_stdout_json(self.finalize_scope_confirmation, workdir)
            self.assertTrue(payload["git_diff_brief.finalize_scope_confirmation_result"]["ok"])
            self.assertEqual(
                [
                    "repository_input_context",
                    "summary_scope",
                    "scope_confirmation_result",
                ],
                payload["git_diff_brief.finalize_scope_confirmation_result"]["confirmed_outputs"],
            )

        assert_route_decision_map(
            self,
            "wf/01_request_scope_alignment/workflow.lgwf",
            "confirm_scope_if_needed",
            {
                "approve": "finalize_scope_confirmation",
                "revise": "capture_request_context",
                "reject": "FAIL_ALL",
            },
        )

    def test_case_collect_git_context_writes_snapshot_and_deduplicates_changed_files(self) -> None:
        changed_files = self.collect_git_context.build_changed_files_index(
            diff_names=["a.py", "a.py", "docs/readme.md"],
            status_lines=["M a.py", "?? wf/workflow.lgwf"],
        )
        self.assertEqual(["a.py", "docs/readme.md", "wf/workflow.lgwf"], changed_files["files"])
        self.assertEqual(3, changed_files["count"])

        snapshot = self.collect_git_context.build_snapshot(
            repo_path=".",
            diff_text="diff --git a.py b.py",
            diff_names=["a.py", "docs/readme.md"],
        )
        self.assertIn("diff_text", snapshot["git_diff_snapshot"])
        self.assertIn("diff_name_only", snapshot["git_diff_snapshot"])
        self.assertIn("status_lines", snapshot["git_diff_snapshot"])
        self.assertEqual(
            ["a.py", "docs/readme.md"],
            snapshot["changed_files_index"]["files"],
        )
        self.assertEqual("placeholder", snapshot["git_collection_log"]["status"])
        self.assertIsInstance(snapshot["git_collection_log"]["warnings"], list)

        with isolated_workdir_with_lgwf_state() as workdir:
            payload = capture_main_stdout_json(self.collect_git_context, workdir)
            output_file = workdir / ".lgwf/git_context_snapshot.json"
            self.assertTrue(output_file.exists())
            persisted = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertIn("git_diff_snapshot", persisted)
            self.assertIn("latest_commit_context", persisted)
            self.assertIn("changed_files_index", persisted)
            self.assertIn("git_collection_log", persisted)
            self.assertEqual(
                ".lgwf/git_context_snapshot.json",
                payload["git_diff_brief.git_context_collection_result"]["output_file"],
            )

    def test_case_derive_validation_suggestions_returns_placeholder_contract(self) -> None:
        result = self.derive_validation_suggestions.build_validation_suggestions()
        self.assertEqual(
            ["git status --short", "git diff --stat", "git log -1 --stat"],
            result["validation_suggestions"],
        )
        self.assertEqual(
            ["git_diff_snapshot", "latest_commit_context", "changed_files_index"],
            result["summary_supporting_context"]["source_of_truth"],
        )
        self.assertTrue(result["summary_supporting_context"]["placeholder"])

        with isolated_workdir_with_lgwf_state() as workdir:
            payload = capture_main_stdout_json(self.derive_validation_suggestions, workdir)
            self.assertTrue(payload["git_diff_brief.validation_suggestions_result"]["ok"])
            self.assertTrue(payload["git_diff_brief.validation_suggestions_result"]["placeholder"])

    def test_case_prepare_delivery_review_falls_back_when_review_context_missing(self) -> None:
        with isolated_workdir_with_lgwf_state() as workdir:
            review = self.prepare_delivery_review.load_review_context(
                workdir / ".lgwf/delivery_review_context.json"
            )
            delivery_input = review["delivery_review_input"]
            self.assertTrue(delivery_input["final_change_brief_markdown"].startswith("# 变更摘要"))
            self.assertIn(
                "缺少 delivery_review_context.json",
                delivery_input["open_delivery_questions"][0],
            )

            payload = capture_main_stdout_json(self.prepare_delivery_review, workdir)
            self.assertEqual(
                ".lgwf/delivery_review_context.json",
                payload["git_diff_brief.prepare_delivery_review_result"]["source_file"],
            )
            self.assertIn(
                "缺少 delivery_review_context.json",
                payload["git_diff_brief.delivery_review_input"]["open_delivery_questions"][0],
            )

    def test_case_delivery_approval_routes_and_finalize_output_contract(self) -> None:
        review_fixture = {
            "delivery_review_input": {
                "final_change_brief_markdown": "# 变更摘要\n\n正文",
                "open_delivery_questions": [],
            }
        }
        with isolated_workdir_with_lgwf_state() as workdir:
            write_utf8_json_fixture(workdir, ".lgwf/delivery_review_context.json", review_fixture)
            for decision in ("approve", "revise", "reject"):
                decision_path = write_utf8_json_fixture(
                    workdir,
                    ".lgwf/delivery_decision.json",
                    {"decision": decision},
                )
                persisted = json.loads(decision_path.read_text(encoding="utf-8"))
                self.assertIn(persisted["decision"], {"approve", "revise", "reject"})

            review = self.prepare_delivery_review.load_review_context(
                workdir / ".lgwf/delivery_review_context.json"
            )
            self.assertEqual(review_fixture["delivery_review_input"], review["delivery_review_input"])

            result = self.finalize_brief_result.build_final_output(
                markdown="# 变更摘要\n\n正文",
                decision={"decision": " Approve ", "comment": "  ok  ", "changes": "ignored"},
                target_path="artifacts/final.md",
            )
            self.assertEqual("# 变更摘要\n\n正文\n", result["final_change_brief_markdown"])
            self.assertEqual("approve", result["delivery_decision"]["decision"])
            self.assertEqual("ok", result["delivery_decision"]["comment"])
            self.assertEqual([], result["delivery_decision"]["changes"])
            self.assertEqual(
                "artifacts/final.md",
                result["run_artifact_index"]["suggested_output_path"],
            )
            self.assertEqual(
                [".lgwf/change_brief_markdown.json", ".lgwf/delivery_decision.json"],
                result["run_artifact_index"]["artifacts"],
            )

            payload = capture_main_stdout_json(self.finalize_brief_result, workdir)
            self.assertTrue(payload["git_diff_brief.finalize_output_result"]["ok"])

        assert_route_decision_map(
            self,
            "wf/04_result_review_and_delivery/workflow.lgwf",
            "confirm_delivery_or_revision",
            {
                "approve": "finalize_output",
                "revise": "present_brief",
                "reject": "FAIL_ALL",
            },
        )

    def test_runtime_guard_and_scripts_do_not_reference_forbidden_runtime_patterns(self) -> None:
        for relative_path in (
            "wf/01_request_scope_alignment/scripts/validate_repo_hint.py",
            "wf/01_request_scope_alignment/scripts/prepare_scope_confirmation.py",
            "wf/01_request_scope_alignment/scripts/finalize_scope_confirmation.py",
            "wf/02_git_context_collection/scripts/collect_git_context.py",
            "wf/03_brief_synthesis/scripts/derive_validation_suggestions.py",
            "wf/04_result_review_and_delivery/scripts/prepare_delivery_review.py",
            "wf/04_result_review_and_delivery/scripts/finalize_brief_result.py",
        ):
            text = (PACKAGE_ROOT / relative_path).read_text(encoding="utf-8").lower()
            for pattern in FORBIDDEN_PATTERNS:
                self.assertNotIn(pattern, text, relative_path)

        with runtime_guard():
            with self.assertRaises(AssertionError):
                subprocess.run(["python", "dummy.py"], check=False)


if __name__ == "__main__":
    unittest.main()
