from __future__ import annotations

import io
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

        def fake_run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            self.assertEqual(kwargs.get("cwd"), str(FACADE_ROOT))
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

        def fake_run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            self.assertEqual(kwargs.get("cwd"), str(FACADE_ROOT))
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

    def test_workflow_id_uses_registry_contract_and_writes_default_input_file(self) -> None:
        calls: list[list[str]] = []
        input_payloads: list[str] = []

        def fake_run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            input_file = Path(args[args.index("--input-json-file") + 1])
            input_payloads.append(input_file.read_text(encoding="utf-8"))
            self.assertEqual(kwargs.get("cwd"), str(FACADE_ROOT))
            return subprocess.CompletedProcess(args=args, returncode=0)

        with mock.patch.object(run_skill_workflow.subprocess, "run", fake_run):
            exit_code = run_skill_workflow.main(["--workflow-id", "wf-fix", "--background"])

        self.assertEqual(exit_code, 0)
        expected_lgwf = FACADE_ROOT / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
        self.assertEqual(calls[0][0:3], [sys.executable, str(expected_lgwf), "run"])
        self.assertIn("--workflow-lgwf", calls[0])
        self.assertIn("workflows/wf-fix/wf/workflow.lgwf", calls[0])
        self.assertIn("--work-dir", calls[0])
        self.assertIn("workflows/wf-fix/ws", calls[0])
        self.assertIn("--input-json-file", calls[0])
        self.assertNotIn("--input-json", calls[0])
        self.assertEqual(input_payloads, ["{}"])

    def test_workflow_id_converts_input_json_to_utf8_input_file(self) -> None:
        calls: list[list[str]] = []
        input_payloads: list[str] = []

        def fake_run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            input_file = Path(args[args.index("--input-json-file") + 1])
            raw = input_file.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            input_payloads.append(raw.decode("utf-8"))
            return subprocess.CompletedProcess(args=args, returncode=0)

        payload = '{"raw_intent":"创建 workflow"}'
        with mock.patch.object(run_skill_workflow.subprocess, "run", fake_run):
            exit_code = run_skill_workflow.main(["--workflow-id", "wf-create-fast", "--input-json", payload])

        self.assertEqual(exit_code, 0)
        self.assertIn("--input-json-file", calls[0])
        self.assertNotIn("--input-json", calls[0])
        self.assertEqual(input_payloads, [payload])

    def test_workflow_id_requires_input_for_input_json_required_contract(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(run_skill_workflow.subprocess, "run") as run_mock, mock.patch.object(sys, "stderr", stderr):
            exit_code = run_skill_workflow.main(["--workflow-id", "wf-create-fast"])

        self.assertEqual(exit_code, 2)
        self.assertIn("requires input JSON", stderr.getvalue())
        run_mock.assert_not_called()

    def test_workflow_id_rejects_auto_human_when_contract_forbids_it(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(run_skill_workflow.subprocess, "run") as run_mock, mock.patch.object(sys, "stderr", stderr):
            exit_code = run_skill_workflow.main(["--workflow-id", "wf-fix", "--auto-human"])

        self.assertEqual(exit_code, 2)
        self.assertIn("forbids --auto-human", stderr.getvalue())
        run_mock.assert_not_called()

    def test_legacy_wf_create_id_is_not_registered(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(run_skill_workflow.subprocess, "run") as run_mock, mock.patch.object(sys, "stderr", stderr):
            exit_code = run_skill_workflow.main(["--workflow-id", "wf-create", "--input-json", '{"raw_intent":"x"}'])

        self.assertEqual(exit_code, 2)
        self.assertIn("unknown workflow id: wf-create", stderr.getvalue())
        run_mock.assert_not_called()

    def test_workflow_id_passes_auto_human_when_contract_is_conditional(self) -> None:
        calls: list[list[str]] = []

        def fake_run(args: list[str], **kwargs) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0)

        with mock.patch.object(run_skill_workflow.subprocess, "run", fake_run):
            exit_code = run_skill_workflow.main(["--workflow-id", "wf-create-fast", "--input-json", '{"raw_intent":"x"}', "--auto-human"])

        self.assertEqual(exit_code, 0)
        self.assertIn("--auto-human", calls[0])


if __name__ == "__main__":
    unittest.main()
