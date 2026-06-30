from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


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

    def test_finalize_output_keeps_markdown_and_decision(self) -> None:
        result = self.delivery_module.build_final_output(
            markdown="# 摘要\n",
            decision={"decision": "approve", "comment": "ok"},
            target_path="artifacts/final.md",
        )
        self.assertEqual("# 摘要\n", result["final_change_brief_markdown"])
        self.assertEqual("approve", result["delivery_decision"]["decision"])
        self.assertEqual("artifacts/final.md", result["run_artifact_index"]["suggested_output_path"])


if __name__ == "__main__":
    unittest.main()
