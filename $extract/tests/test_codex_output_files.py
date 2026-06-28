from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from lgwf_client.runners.codex_runner.runner import CodexRunner


class CodexOutputFilesTest(unittest.TestCase):
    def test_prompt_text_includes_output_file_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = CodexRunner(workflow_root=root, workspace_root=root)
            output = root / ".lgwf" / "reason.md"
            prompt, _main, _contexts = runner._prompt_text(
                str(root),
                "write reason",
                None,
                output_file_paths=[output],
            )

        self.assertIn("Codex-written file outputs", prompt)
        self.assertIn(str(output), prompt)

    def test_output_file_paths_must_be_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = CodexRunner(workflow_root=root, workspace_root=root)
            with self.assertRaisesRegex(ValueError, "output_files must be a list"):
                runner._output_file_paths(root, "not-list")

    def test_output_file_paths_reject_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runner = CodexRunner(workflow_root=root, workspace_root=root)
            with self.assertRaisesRegex(ValueError, "use output_json"):
                runner._output_file_paths(root, [".lgwf/data.json"])

    def test_validate_output_files_records_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / ".lgwf" / "reason.md"
            output.parent.mkdir()
            output.write_text("中文 reason\n", encoding="utf-8")
            result = {"metadata": {}, "artifacts": [], "changed_files": []}

            expected_size = output.stat().st_size

            CodexRunner(workflow_root=root, workspace_root=root)._validate_output_files(
                [output],
                result,
            )

        self.assertEqual(result["metadata"]["output_files"][0]["size_bytes"], expected_size)
        self.assertEqual(result["artifacts"][0]["type"], "file_output")

    def test_validate_output_files_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = {"metadata": {}, "artifacts": [], "changed_files": []}

            with self.assertRaisesRegex(ValueError, "Codex did not create"):
                CodexRunner(workflow_root=root, workspace_root=root)._validate_output_files(
                    [root / ".lgwf" / "missing.md"],
                    result,
                )


if __name__ == "__main__":
    unittest.main()
