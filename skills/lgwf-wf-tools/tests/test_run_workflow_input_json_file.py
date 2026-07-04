from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path


FACADE_ROOT = Path(__file__).resolve().parents[1]
VENDOR_SCRIPTS = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts"
if str(VENDOR_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(VENDOR_SCRIPTS))

import run_workflow  # noqa: E402


class RunWorkflowInputJsonFileTests(unittest.TestCase):
    def test_input_json_file_reads_utf8_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            input_path.write_text('{"raw_intent":"创建 workflow"}', encoding="utf-8")

            args = run_workflow._build_parser().parse_args(
                [
                    "--workflow-json",
                    "workflow.json",
                    "--work-dir",
                    "ws",
                    "--input-json-file",
                    str(input_path),
                ]
            )

            stderr = io.StringIO()
            exit_code = run_workflow._resolve_input_json_arg(args, stderr)

            self.assertIsNone(exit_code)
            self.assertEqual(args.input_json, '{"raw_intent":"创建 workflow"}')
            self.assertEqual(stderr.getvalue(), "")

    def test_input_json_at_file_reads_utf8_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            input_path.write_text('{"repo_path":"."}', encoding="utf-8")

            args = run_workflow._build_parser().parse_args(
                [
                    "--workflow-json",
                    "workflow.json",
                    "--work-dir",
                    "ws",
                    "--input-json",
                    f"@{input_path}",
                ]
            )

            stderr = io.StringIO()
            exit_code = run_workflow._resolve_input_json_arg(args, stderr)

            self.assertIsNone(exit_code)
            self.assertEqual(args.input_json, '{"repo_path":"."}')

    def test_input_json_file_rejects_explicit_input_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            input_path.write_text('{"repo_path":"."}', encoding="utf-8")

            args = run_workflow._build_parser().parse_args(
                [
                    "--workflow-json",
                    "workflow.json",
                    "--work-dir",
                    "ws",
                    "--input-json",
                    '{"other":true}',
                    "--input-json-file",
                    str(input_path),
                ]
            )

            stderr = io.StringIO()
            exit_code = run_workflow._resolve_input_json_arg(args, stderr)

            self.assertEqual(exit_code, 2)
            self.assertIn("cannot be combined", stderr.getvalue())

    def test_input_json_file_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            input_path.write_text('{"repo_path":', encoding="utf-8")

            args = run_workflow._build_parser().parse_args(
                [
                    "--workflow-json",
                    "workflow.json",
                    "--work-dir",
                    "ws",
                    "--input-json-file",
                    str(input_path),
                ]
            )

            stderr = io.StringIO()
            exit_code = run_workflow._resolve_input_json_arg(args, stderr)

            self.assertEqual(2, exit_code)
            self.assertIn("valid JSON", stderr.getvalue())

    def test_runtime_paths_resolve_work_dir_to_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp) / "ws"
            args = run_workflow._build_parser().parse_args(
                [
                    "--workflow-json",
                    "workflow.json",
                    "--work-dir",
                    str(work_dir),
                ]
            )

            run_workflow._resolve_runtime_paths(args)

            self.assertEqual(str(work_dir.resolve()), args.work_dir)


if __name__ == "__main__":
    unittest.main()
