from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


FACADE_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = FACADE_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import run_skill_workflow  # noqa: E402


class RunSkillWorkflowTests(unittest.TestCase):
    def test_proxies_arguments_to_bundled_lgwf_run(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=7)

        argv = [
            "--workflow-lgwf",
            "wf/workflow.lgwf",
            "--work-dir",
            "ws",
            "--input-json",
            '{"repo_path":"."}',
            "--background",
        ]

        with mock.patch.object(run_skill_workflow.subprocess, "run", fake_run):
            exit_code = run_skill_workflow.main(argv)

        self.assertEqual(exit_code, 7)
        self.assertEqual(len(calls), 1)
        expected_lgwf = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
        self.assertEqual(calls[0], [sys.executable, str(expected_lgwf), "run", *argv])

    def test_proxies_input_json_file_argument(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str]) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0)

        argv = [
            "--workflow-lgwf",
            "skills/git-diff-brief/wf/workflow.lgwf",
            "--work-dir",
            "skills/git-diff-brief/ws",
            "--input-json-file",
            "D:/tmp/lgwf-input.json",
            "--background",
        ]

        with mock.patch.object(run_skill_workflow.subprocess, "run", fake_run):
            exit_code = run_skill_workflow.main(argv)

        self.assertEqual(exit_code, 0)
        expected_lgwf = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
        self.assertEqual(calls[0], [sys.executable, str(expected_lgwf), "run", *argv])


if __name__ == "__main__":
    unittest.main()
