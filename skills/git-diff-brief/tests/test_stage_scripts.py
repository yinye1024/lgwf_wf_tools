from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def load_module(relative_path: str, module_name: str):
    path = PACKAGE_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class StageScriptsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scope_module = load_module(
            "wf/01_request_scope_alignment/scripts/validate_repo_hint.py",
            "git_diff_brief_validate_repo_hint",
        )
        cls.git_module = load_module(
            "wf/02_git_context_collection/scripts/collect_git_context.py",
            "git_diff_brief_collect_git_context",
        )
        cls.delivery_module = load_module(
            "wf/04_result_review_and_delivery/scripts/finalize_brief_result.py",
            "git_diff_brief_finalize_brief_result",
        )
        cls.commit_action_module = load_module(
            "wf/05_git_commit/scripts/execute_commit_action.py",
            "git_diff_brief_execute_commit_action",
        )
        cls.token_usage_module = load_module(
            "wf/05_git_commit/scripts/write_token_usage_by_node.py",
            "git_diff_brief_write_token_usage_by_node",
        )

    def test_normalize_repo_hint_rejects_blank_and_state_dir(self) -> None:
        with self.assertRaises(ValueError):
            self.scope_module.normalize_repo_hint("  ")
        with self.assertRaises(ValueError):
            self.scope_module.normalize_repo_hint(".lgwf/run")

    def test_build_changed_files_index_deduplicates_paths(self) -> None:
        result = self.git_module.build_changed_files_index(
            diff_names=["a.py", "a.py", "docs/readme.md"],
            status_lines=["M a.py", "?? wf/workflow.lgwf"],
        )
        self.assertEqual(["a.py", "docs/readme.md", "wf/workflow.lgwf"], result["files"])
        self.assertEqual(3, result["count"])

    def test_read_stdin_payload_prefers_workflow_input(self) -> None:
        stdin = io.StringIO(json.dumps({"input": {"repo_hint": "skills/git-diff-brief"}}))
        with mock.patch("sys.stdin", stdin):
            payload = self.scope_module.read_stdin_payload()

        self.assertEqual({"repo_hint": "skills/git-diff-brief"}, payload)

    def test_collect_git_snapshot_reads_real_worktree_diff_and_latest_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "测试用户"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            tracked = repo / "tracked.txt"
            tracked.write_text("第一行\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "commit", "-m", "initial commit"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            tracked.write_text("第一行\n第二行\n", encoding="utf-8")
            (repo / "new.txt").write_text("新增\n", encoding="utf-8")

            snapshot = self.git_module.collect_git_snapshot(str(repo))

        self.assertEqual("ok", snapshot["git_collection_log"]["status"])
        self.assertEqual([], snapshot["git_collection_log"]["warnings"])
        self.assertIn("tracked.txt", snapshot["git_diff_snapshot"]["diff_name_only"])
        self.assertIn(" M tracked.txt", snapshot["git_diff_snapshot"]["status_lines"])
        self.assertIn("?? new.txt", snapshot["git_diff_snapshot"]["status_lines"])
        self.assertIn("diff --git", snapshot["git_diff_snapshot"]["diff_text"])
        self.assertEqual("initial commit", snapshot["latest_commit_context"]["subject"])
        self.assertIn("tracked.txt", snapshot["changed_files_index"]["files"])
        self.assertIn("new.txt", snapshot["changed_files_index"]["files"])

    def test_build_compact_context_truncates_large_diff_and_keeps_snapshot_full(self) -> None:
        diff_text = "diff --git a/a.py b/a.py\n" + ("+x\n" * 100)
        snapshot = self.git_module.build_snapshot(
            repo_path=".",
            diff_text=diff_text,
            diff_stat=" a.py | 100 +++++\n",
            diff_names=["a.py", "vendor/blob.zip"],
            status_lines=[" M a.py", "?? vendor/blob.zip"],
        )
        compact = self.git_module.build_compact_context(snapshot, max_total_chars=50, max_file_chars=30)

        self.assertEqual(diff_text, snapshot["git_diff_snapshot"]["diff_text"])
        self.assertEqual(50, compact["context_budget"]["max_total_diff_chars"])
        self.assertIn("a.py", compact["context_budget"]["truncated_files"])
        self.assertIn("vendor/blob.zip", compact["context_budget"]["heavy_files"])
        self.assertLessEqual(compact["git_diff_compact"]["diff_snippets"][0]["retained_chars"], 30)

    def test_collect_git_snapshot_scopes_to_requested_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "测试用户"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            in_scope = repo / "skills" / "git-diff-brief" / "tracked.txt"
            out_scope = repo / "skills" / "lgwf-wf-tools" / "tracked.txt"
            in_scope.parent.mkdir(parents=True)
            out_scope.parent.mkdir(parents=True)
            in_scope.write_text("old\n", encoding="utf-8")
            out_scope.write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo, check=True, capture_output=True, text=True)
            in_scope.write_text("old\nnew\n", encoding="utf-8")
            out_scope.write_text("old\nnew\n", encoding="utf-8")
            new_in_scope = repo / "skills" / "git-diff-brief" / "new.txt"
            new_in_scope.write_text("新增\n", encoding="utf-8")

            snapshot = self.git_module.collect_git_snapshot(str(repo / "skills" / "git-diff-brief"))

        self.assertEqual("skills/git-diff-brief", snapshot["git_collection_log"]["relative_scope"])
        self.assertEqual(2, snapshot["changed_files_index"]["count"])
        self.assertIn("skills/git-diff-brief/tracked.txt", snapshot["git_diff_snapshot"]["diff_name_only"])
        self.assertNotIn("skills/lgwf-wf-tools/tracked.txt", snapshot["git_diff_snapshot"]["diff_name_only"])
        self.assertIn("?? skills/git-diff-brief/new.txt", snapshot["git_diff_snapshot"]["status_lines"])
        self.assertNotIn("skills/lgwf-wf-tools/tracked.txt", snapshot["git_diff_snapshot"]["diff_text"])

    def test_finalize_output_keeps_markdown_and_decision(self) -> None:
        result = self.delivery_module.build_final_output(
            markdown="# 摘要\n",
            decision={"decision": "approve", "comment": "ok"},
            target_path="artifacts/final.md",
        )
        self.assertEqual("# 摘要\n", result["final_change_brief_markdown"])
        self.assertEqual("approve", result["delivery_decision"]["decision"])
        self.assertEqual("artifacts/final.md", result["run_artifact_index"]["suggested_output_path"])

    def test_commit_action_none_does_not_run_git(self) -> None:
        decision = self.delivery_module.normalize_delivery_decision(
            {"approval": "approve"},
            commit_message_suggestion="chore(git-diff-brief): summarize scoped changes",
        )
        git_context = {
            "git_collection_log": {
                "repo_path": "D:/repo",
                "relative_scope": "skills/git-diff-brief",
            }
        }
        plan = self.delivery_module.build_commit_plan(decision, git_context)
        with mock.patch("subprocess.run") as run:
            result = self.commit_action_module.execute_commit_action(plan)

        run.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertFalse(result["executed"])
        self.assertEqual("none", result["action"])

    def test_commit_action_stage_uses_confirmed_relative_scope(self) -> None:
        decision = self.delivery_module.normalize_delivery_decision(
            {
                "approval": "approve",
                "commit_action": "stage",
                "stage_scope": "target_scope",
            },
            commit_message_suggestion="chore(git-diff-brief): summarize scoped changes",
        )
        git_context = {
            "git_collection_log": {
                "repo_path": "D:/repo",
                "relative_scope": "skills/git-diff-brief",
            }
        }
        plan = self.delivery_module.build_commit_plan(decision, git_context)
        completed = subprocess.CompletedProcess(
            args=["git", "add", "--all", "--", "skills/git-diff-brief"],
            returncode=0,
            stdout="",
            stderr="",
        )
        with mock.patch("subprocess.run", return_value=completed) as run:
            result = self.commit_action_module.execute_commit_action(plan)

        run.assert_called_once()
        self.assertEqual(["git", "add", "--all", "--", "skills/git-diff-brief"], run.call_args.args[0])
        self.assertEqual("D:/repo", run.call_args.kwargs["cwd"])
        self.assertTrue(result["ok"])
        self.assertTrue(result["executed"])

    def test_commit_action_commit_adds_scope_then_commits_message(self) -> None:
        decision = self.delivery_module.normalize_delivery_decision(
            {
                "approval": "approve",
                "commit_action": "commit",
                "stage_scope": "target_scope",
                "commit_message": "fix(git-diff-brief): add commit assistance",
            },
            commit_message_suggestion="chore(git-diff-brief): summarize scoped changes",
        )
        git_context = {
            "git_collection_log": {
                "repo_path": "D:/repo",
                "relative_scope": "skills/git-diff-brief",
            }
        }
        plan = self.delivery_module.build_commit_plan(decision, git_context)
        completed = subprocess.CompletedProcess(args=["git"], returncode=0, stdout="", stderr="")
        with mock.patch("subprocess.run", return_value=completed) as run:
            result = self.commit_action_module.execute_commit_action(plan)

        calls = [call.args[0] for call in run.call_args_list]
        self.assertEqual(
            [
                ["git", "add", "--all", "--", "skills/git-diff-brief"],
                ["git", "commit", "-m", "fix(git-diff-brief): add commit assistance"],
                ["git", "rev-parse", "HEAD"],
                ["git", "log", "-1", "--pretty=%s"],
            ],
            calls,
        )
        self.assertTrue(result["ok"])
        self.assertEqual("commit", result["action"])

    def test_commit_action_commit_requires_message_and_scope(self) -> None:
        invalid_decision = self.delivery_module.normalize_delivery_decision(
            {"approval": "approve", "commit_action": "push"},
            commit_message_suggestion="chore(git-diff-brief): summarize scoped changes",
        )
        invalid_plan = self.delivery_module.build_commit_plan(invalid_decision, {"git_collection_log": {}})
        self.assertFalse(invalid_plan["ok"])
        self.assertIn("commit_action", invalid_plan["error"])

        git_context_without_scope = {"git_collection_log": {"repo_path": "D:/repo"}}
        decision_without_message = self.delivery_module.normalize_delivery_decision(
            {"approval": "approve", "commit_action": "commit", "commit_message": ""},
            commit_message_suggestion="",
        )
        plan_without_message = self.delivery_module.build_commit_plan(decision_without_message, git_context_without_scope)
        self.assertFalse(plan_without_message["ok"])
        self.assertIn("commit_message", plan_without_message["error"])

        decision_with_message = self.delivery_module.normalize_delivery_decision(
            {"approval": "approve", "commit_action": "stage"},
            commit_message_suggestion="chore(git-diff-brief): summarize scoped changes",
        )
        plan_without_scope = self.delivery_module.build_commit_plan(decision_with_message, git_context_without_scope)
        self.assertFalse(plan_without_scope["ok"])
        self.assertIn("relative_scope", plan_without_scope["error"])

    def test_commit_message_suggestion_has_stable_fallback(self) -> None:
        suggestion = self.delivery_module.resolve_commit_message_suggestion(
            review_context={},
            summary_context={"change_overview": ["补齐真实 Git 采集"]},
            git_context={"git_collection_log": {"relative_scope": "skills/git-diff-brief"}},
        )
        self.assertEqual("chore(git-diff-brief): summarize scoped git diff changes", suggestion["message"])
        self.assertIn("skills/git-diff-brief", suggestion["rationale"])

    def test_commit_actions_stage_and_commit_real_temporary_repo_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "测试用户"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )
            in_scope = repo / "skills" / "git-diff-brief" / "tracked.txt"
            out_scope = repo / "skills" / "lgwf-wf-tools" / "tracked.txt"
            in_scope.parent.mkdir(parents=True)
            out_scope.parent.mkdir(parents=True)
            in_scope.write_text("old\n", encoding="utf-8")
            out_scope.write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo, check=True, capture_output=True, text=True)

            in_scope.write_text("old\nnew\n", encoding="utf-8")
            out_scope.write_text("old\nnew\n", encoding="utf-8")
            git_context = {
                "git_collection_log": {
                    "repo_path": repo.as_posix(),
                    "relative_scope": "skills/git-diff-brief",
                }
            }
            stage_decision = self.delivery_module.normalize_delivery_decision(
                {"approval": "approve", "commit_action": "stage"},
                commit_message_suggestion="chore(git-diff-brief): summarize scoped changes",
            )
            stage_result = self.commit_action_module.execute_commit_action(
                self.delivery_module.build_commit_plan(stage_decision, git_context)
            )
            staged = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertTrue(stage_result["ok"])
            self.assertEqual(["skills/git-diff-brief/tracked.txt"], staged)

            commit_decision = self.delivery_module.normalize_delivery_decision(
                {
                    "approval": "approve",
                    "commit_action": "commit",
                    "commit_message": "fix(git-diff-brief): add commit assistance",
                },
                commit_message_suggestion="chore(git-diff-brief): summarize scoped changes",
            )
            commit_result = self.commit_action_module.execute_commit_action(
                self.delivery_module.build_commit_plan(commit_decision, git_context)
            )
            latest_subject = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            unstaged = subprocess.run(
                ["git", "diff", "--name-only"],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertTrue(commit_result["ok"], commit_result)
            self.assertRegex(commit_result["commit_hash"], r"^[0-9a-f]{40}$")
            self.assertEqual("fix(git-diff-brief): add commit assistance", commit_result["commit_subject"])
            self.assertEqual("fix(git-diff-brief): add commit assistance", latest_subject)
            self.assertEqual(["skills/lgwf-wf-tools/tracked.txt"], unstaged)

    def test_token_usage_report_reads_codex_metadata_and_flags_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / ".lgwf" / "codex" / "inspect_repo_state_codex_prompt-run"
            root.mkdir(parents=True)
            (root / "metadata.json").write_text(
                json.dumps(
                    {
                        "token_usage": {
                            "input_tokens": 160000,
                            "cached_input_tokens": 1000,
                            "output_tokens": 10,
                            "reasoning_output_tokens": 5,
                            "total_tokens": 160010,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report = self.token_usage_module.collect_token_usage(Path(temp_dir) / ".lgwf" / "codex")

        self.assertEqual("inspect_repo_state", report["nodes"][0]["node_id"])
        self.assertTrue(report["nodes"][0]["over_budget"])
        self.assertEqual(["inspect_repo_state"], report["over_budget_nodes"])


if __name__ == "__main__":
    unittest.main()
