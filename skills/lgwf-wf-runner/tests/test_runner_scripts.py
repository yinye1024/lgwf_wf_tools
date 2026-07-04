from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


RUNNER_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = RUNNER_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import launch_workflow  # noqa: E402
import list_sessions  # noqa: E402
import runner_common  # noqa: E402
import status_session  # noqa: E402


class FakeStdout:
    def __init__(self) -> None:
        self.buffer = io.BytesIO()


class RunnerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.stack = tempfile.TemporaryDirectory()
        self.root = Path(self.stack.name)
        self.facade_root = self.root / "lgwf-wf-tools"
        self.runner_root = self.root / "lgwf-wf-runner"
        self._write_facade()

    def tearDown(self) -> None:
        self.stack.cleanup()

    def _write_facade(self, *, registry_overrides: dict | None = None) -> None:
        registry_item = {
            "id": "wf-create",
            "description": "fake create workflow",
            "workflow_lgwf": "workflows/wf-create/wf/workflow.lgwf",
            "work_dir": "workflows/wf-create/ws",
            "agents_md": "workflows/wf-create/AGENTS.md",
        }
        if registry_overrides:
            registry_item.update(registry_overrides)
        self._write_json(self.facade_root / "registry.json", {"workflows": [registry_item]})
        (self.facade_root / "vendor" / "lgwf-client-assist" / "scripts").mkdir(parents=True, exist_ok=True)
        (self.facade_root / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py").write_text(
            "# fake lgwf\n",
            encoding="utf-8",
        )
        (self.facade_root / "workflows" / "wf-create" / "wf").mkdir(parents=True, exist_ok=True)
        (self.facade_root / "workflows" / "wf-create" / "wf" / "workflow.lgwf").write_text(
            "WORKFLOW fake\n",
            encoding="utf-8",
        )
        (self.facade_root / "workflows" / "wf-create" / "AGENTS.md").write_text(
            "# fake agents\n",
            encoding="utf-8",
        )

    def _write_json(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _resolve(self, **overrides) -> dict:
        params = {
            "facade_root": self.facade_root,
            "runner_root": self.runner_root,
            "workflow_id": "wf-create",
            "target_slug": "LGWF Thinking",
            "facade_session_id": None,
            "create": False,
        }
        params.update(overrides)
        return runner_common.resolve_work_dir(**params)


class ResolveWorkDirTests(RunnerTestCase):
    def test_resolve_work_dir_uses_sessions_under_base_for_different_sessions(self) -> None:
        first = self._resolve(facade_session_id="Session One")
        second = self._resolve(facade_session_id="Session Two")

        self.assertNotEqual(first["resolved_work_dir"], second["resolved_work_dir"])
        self.assertTrue(first["resolved_work_dir"].endswith(r"ws\sessions\wf-create\session-one"))
        self.assertTrue(second["resolved_work_dir"].endswith(r"ws\sessions\wf-create\session-two"))

    def test_resolve_work_dir_create_makes_resolved_directory(self) -> None:
        resolved = self._resolve(facade_session_id="Create Me", create=True)

        self.assertTrue(Path(resolved["resolved_work_dir"]).is_dir())

    def test_resolve_work_dir_rejects_unknown_workflow_id(self) -> None:
        with self.assertRaisesRegex(KeyError, "missing"):
            self._resolve(workflow_id="missing")

    def test_resolve_work_dir_rejects_unsafe_registry_paths(self) -> None:
        unsafe_cases = [
            {"workflow_lgwf": str((self.root / "outside.lgwf").resolve())},
            {"work_dir": "../outside"},
            {"agents_md": ""},
        ]

        for overrides in unsafe_cases:
            with self.subTest(overrides=overrides):
                self._write_facade(registry_overrides=overrides)
                with self.assertRaises(ValueError):
                    self._resolve()

    def test_resolve_work_dir_slugifies_session_id_and_keeps_path_under_base(self) -> None:
        resolved = self._resolve(facade_session_id="中文 / Odd Session !!")
        base = Path(resolved["base_work_dir"])
        work_dir = Path(resolved["resolved_work_dir"])

        self.assertEqual(resolved["facade_session_id"], "odd-session")
        self.assertEqual(work_dir.relative_to(base).parts[0], "sessions")

    def test_run_command_replaces_non_utf8_output_bytes(self) -> None:
        calls: list[dict] = []

        def fake_run(args, **kwargs):
            calls.append(kwargs)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

        with mock.patch.object(runner_common.subprocess, "run", fake_run):
            runner_common.run_command(["python", "--version"], cwd=self.root, timeout=3)

        self.assertEqual(calls[0]["encoding"], "utf-8")
        self.assertEqual(calls[0]["errors"], "replace")

    def test_emit_json_writes_utf8_bytes(self) -> None:
        fake_stdout = FakeStdout()
        with mock.patch.object(sys, "stdout", fake_stdout):
            with self.assertRaises(SystemExit) as exit_context:
                runner_common.emit_json({"text": "bad � char"})

        self.assertEqual(exit_context.exception.code, 0)
        self.assertIn('"bad � char"', fake_stdout.buffer.getvalue().decode("utf-8"))


class LaunchWorkflowTests(RunnerTestCase):
    def test_read_input_json_rejects_inline_and_file_inputs_together(self) -> None:
        args = argparse.Namespace(input_json="{}", input_json_file=str(self.root / "input.json"))

        with self.assertRaisesRegex(ValueError, "只允许提供"):
            launch_workflow.read_input_json(args)

    def test_launch_writes_manifest_and_uses_isolated_work_dir(self) -> None:
        calls: list[tuple[list[str], Path, int | None]] = []

        def fake_run_command(args: list[str], *, cwd: Path, timeout: int | None = None):
            calls.append((args, cwd, timeout))
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"session_id": "runtime-1", "pid": 1234}),
                stderr="",
            )

        argv = [
            "launch_workflow.py",
            "--facade-root",
            str(self.facade_root),
            "--runner-root",
            str(self.runner_root),
            "--workflow-id",
            "wf-create",
            "--target-slug",
            "LGWF Thinking",
            "--facade-session-id",
            "session-1",
            "--input-json",
            '{"raw_intent":"create thinking"}',
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(launch_workflow, "run_command", fake_run_command),
            mock.patch.object(sys, "stdout", FakeStdout()),
        ):
            with self.assertRaises(SystemExit) as exit_context:
                launch_workflow.main()

        self.assertEqual(exit_context.exception.code, 0)
        self.assertEqual(len(calls), 1)
        command, cwd, timeout = calls[0]
        self.assertEqual(cwd, self.facade_root.resolve())
        self.assertEqual(timeout, 60)
        self.assertIn("run", command)
        self.assertIn("--workflow-lgwf", command)
        self.assertIn("--work-dir", command)
        self.assertIn("--input-json", command)
        self.assertIn("--background", command)
        work_dir = Path(command[command.index("--work-dir") + 1])
        self.assertTrue(str(work_dir).endswith(r"ws\sessions\wf-create\session-1"))

        manifest_path = work_dir / ".lgwf" / "main_agent" / "facade_session.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["workflow_id"], "wf-create")
        self.assertEqual(manifest["target_slug"], "LGWF Thinking")
        self.assertEqual(manifest["facade_session_id"], "session-1")
        self.assertEqual(manifest["runtime_session_id"], "runtime-1")
        self.assertEqual(manifest["pid"], 1234)
        self.assertEqual(Path(manifest["resolved_work_dir"]), work_dir)
        self.assertEqual(manifest["input_json"], {"raw_intent": "create thinking"})

    def test_launch_passes_input_json_file_to_runtime(self) -> None:
        calls: list[tuple[list[str], Path, int | None]] = []
        input_path = self.root / "input.json"
        input_path.write_text('{"raw_intent":"创建 workflow"}', encoding="utf-8")

        def fake_run_command(args: list[str], *, cwd: Path, timeout: int | None = None):
            calls.append((args, cwd, timeout))
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=json.dumps({"session_id": "runtime-1", "pid": 1234}),
                stderr="",
            )

        argv = [
            "launch_workflow.py",
            "--facade-root",
            str(self.facade_root),
            "--runner-root",
            str(self.runner_root),
            "--workflow-id",
            "wf-create",
            "--target-slug",
            "LGWF Thinking",
            "--facade-session-id",
            "session-1",
            "--input-json-file",
            str(input_path),
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(launch_workflow, "run_command", fake_run_command),
            mock.patch.object(sys, "stdout", FakeStdout()),
        ):
            with self.assertRaises(SystemExit) as exit_context:
                launch_workflow.main()

        self.assertEqual(exit_context.exception.code, 0)
        command, _, _ = calls[0]
        self.assertIn("--input-json-file", command)
        self.assertNotIn("--input-json", command)
        self.assertEqual(command[command.index("--input-json-file") + 1], str(input_path))
        work_dir = Path(command[command.index("--work-dir") + 1])
        manifest_path = work_dir / ".lgwf" / "main_agent" / "facade_session.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["input_json"], {"raw_intent": "创建 workflow"})


class StatusSessionTests(RunnerTestCase):
    def _write_manifest(
        self,
        *,
        workflow_id: str = "wf-create",
        facade_session_id: str = "session-1",
        runtime_session_id: str = "runtime-1",
        pid: int | None = 1234,
    ) -> Path:
        work_dir = self.runner_root / "ws" / "sessions" / workflow_id / facade_session_id
        manifest = {
            "workflow_id": workflow_id,
            "facade_session_id": facade_session_id,
            "runtime_session_id": runtime_session_id,
            "pid": pid,
            "resolved_work_dir": str(work_dir.resolve()),
            "runner_root": str(self.runner_root.resolve()),
        }
        manifest_path = work_dir / ".lgwf" / "main_agent" / "facade_session.json"
        self._write_json(manifest_path, manifest)
        return manifest_path

    def test_status_session_uses_manifest_work_dir_and_runtime_session_id(self) -> None:
        manifest_path = self._write_manifest(runtime_session_id="runtime-1", pid=999)
        calls: list[list[str]] = []

        def fake_run_command(args: list[str], *, cwd: Path, timeout: int | None = None):
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"phase":"running"}', stderr="")

        argv = [
            "status_session.py",
            "--facade-root",
            str(self.facade_root),
            "--runner-root",
            str(self.runner_root),
            "--facade-session-id",
            "session-1",
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(status_session, "run_command", fake_run_command),
            mock.patch.object(sys, "stdout", FakeStdout()),
        ):
            with self.assertRaises(SystemExit) as exit_context:
                status_session.main()

        self.assertEqual(exit_context.exception.code, 0)
        command = calls[0]
        self.assertEqual(command[command.index("--work-dir") + 1], str(manifest_path.parents[2].resolve()))
        self.assertEqual(command[command.index("--session-id") + 1], "runtime-1")
        self.assertNotIn("--pid", command)

    def test_status_session_uses_pid_when_runtime_session_id_missing(self) -> None:
        self._write_manifest(runtime_session_id="", pid=4321)
        calls: list[list[str]] = []

        def fake_run_command(args: list[str], *, cwd: Path, timeout: int | None = None):
            calls.append(args)
            return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"phase":"running"}', stderr="")

        argv = [
            "status_session.py",
            "--facade-root",
            str(self.facade_root),
            "--runner-root",
            str(self.runner_root),
            "--facade-session-id",
            "session-1",
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(status_session, "run_command", fake_run_command),
            mock.patch.object(sys, "stdout", FakeStdout()),
        ):
            with self.assertRaises(SystemExit) as exit_context:
                status_session.main()

        self.assertEqual(exit_context.exception.code, 0)
        self.assertEqual(calls[0][calls[0].index("--pid") + 1], "4321")
        self.assertNotIn("--session-id", calls[0])

    def test_status_session_fails_when_manifest_missing_or_duplicated(self) -> None:
        with self.assertRaises(FileNotFoundError):
            status_session.find_manifest(self.runner_root, "missing")

        self._write_manifest(workflow_id="wf-create", facade_session_id="dup")
        self._write_manifest(workflow_id="wf-other", facade_session_id="dup")
        with self.assertRaises(RuntimeError):
            status_session.find_manifest(self.runner_root, "dup")


class ListSessionsTests(RunnerTestCase):
    def _write_manifest(self, workflow_id: str, facade_session_id: str) -> None:
        work_dir = self.runner_root / "ws" / "sessions" / workflow_id / facade_session_id
        self._write_json(
            work_dir / ".lgwf" / "main_agent" / "facade_session.json",
            {
                "workflow_id": workflow_id,
                "target_slug": workflow_id,
                "facade_session_id": facade_session_id,
                "runtime_session_id": f"runtime-{facade_session_id}",
                "pid": 1,
                "resolved_work_dir": str(work_dir.resolve()),
            },
        )

    def test_list_sessions_scans_filters_and_sorts_sessions(self) -> None:
        self._write_manifest("wf-create", "20240101-a")
        self._write_manifest("wf-create", "20240103-c")
        self._write_manifest("wf-other", "20240102-b")

        argv = [
            "list_sessions.py",
            "--facade-root",
            str(self.facade_root),
            "--runner-root",
            str(self.runner_root),
            "--workflow-id",
            "wf-create",
        ]
        fake_stdout = FakeStdout()
        with mock.patch.object(sys, "argv", argv), mock.patch.object(sys, "stdout", fake_stdout):
            with self.assertRaises(SystemExit) as exit_context:
                list_sessions.main()

        self.assertEqual(exit_context.exception.code, 0)
        payload = json.loads(fake_stdout.buffer.getvalue().decode("utf-8"))
        self.assertEqual([item["facade_session_id"] for item in payload["sessions"]], ["20240103-c", "20240101-a"])
        self.assertTrue(all(item["workflow_id"] == "wf-create" for item in payload["sessions"]))


if __name__ == "__main__":
    unittest.main()
