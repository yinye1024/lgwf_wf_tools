from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WHEEL = REPO_ROOT / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "assets" / "lgwf-0.1.2-py3-none-any.whl"
RUNTIME_SCRIPTS = REPO_ROOT / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "scripts"


class ExtractedWheel:
    def __enter__(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        with zipfile.ZipFile(WHEEL) as archive:
            archive.extractall(self.root)
        sys.path.insert(0, str(self.root))
        return self.root

    def __exit__(self, exc_type, exc, tb):
        try:
            sys.path.remove(str(self.root))
        except ValueError:
            pass
        for name in list(sys.modules):
            if name == "lgwf_client" or name.startswith("lgwf_client."):
                del sys.modules[name]
        self.temp_dir.cleanup()


class CodexStatusDiagnosticsTest(unittest.TestCase):
    def test_process_status_display_includes_codex_diagnostics(self) -> None:
        sys.path.insert(0, str(RUNTIME_SCRIPTS))
        try:
            process_status = importlib.import_module("lgwf_env_init.process_status")
            display_payload = process_status.build_display_status(
                {
                    "phase": "running",
                    "current_node": "design_steps_react",
                    "current_capability": "exec.codex_prompt",
                    "codex": {
                        "status": "running",
                        "current_instruction_id": "design_steps_react:codex_prompt",
                        "track_dir": "D:/work/.lgwf/codex/design_steps",
                        "track_files": {
                            "stdout": {"path": "D:/work/.lgwf/codex/design_steps/stdout.txt"},
                            "stderr": {"path": "D:/work/.lgwf/codex/design_steps/stderr.txt"},
                        },
                        "output_json": {"path": "D:/work/.lgwf/step_designs_proposal.json"},
                        "last_file_update_unix": 123.0,
                    },
                }
            )
        finally:
            try:
                sys.path.remove(str(RUNTIME_SCRIPTS))
            except ValueError:
                pass
            for name in list(sys.modules):
                if name == "lgwf_env_init" or name.startswith("lgwf_env_init."):
                    del sys.modules[name]

        text = display_payload["status_text"]
        self.assertIn("design_steps_react:codex_prompt", text)
        self.assertIn("D:/work/.lgwf/codex/design_steps", text)
        self.assertIn("stdout.txt", text)
        self.assertIn("stderr.txt", text)
        self.assertIn("step_designs_proposal.json", text)

    def test_live_status_and_token_status_expose_files_output_and_process(self) -> None:
        with ExtractedWheel():
            track_store = importlib.import_module("lgwf_client.runners.codex_runner.track_store")
            codex_command = importlib.import_module("lgwf_client.commands.codex")

            with tempfile.TemporaryDirectory() as temp:
                work_dir = Path(temp)
                track_dir = work_dir / ".lgwf" / "codex" / "demo-000"
                track_dir.mkdir(parents=True)
                stdout_path = track_dir / "stdout.txt"
                stderr_path = track_dir / "stderr.txt"
                output_json_path = work_dir / ".lgwf" / "create_requirements_proposal.json"
                stdout_path.write_text("still running\n", encoding="utf-8")
                stderr_path.write_text("", encoding="utf-8")

                track_store.write_live_status(
                    work_dir,
                    {"id": "propose_requirements_react:codex_prompt", "capability": "exec.codex_prompt"},
                    track_dir,
                    status="running",
                    live_turn_count=0,
                    live_token_usage={
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "total_tokens": 0,
                        "cached_input_tokens": 0,
                        "reasoning_output_tokens": 0,
                    },
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    output_json_path=output_json_path,
                    output_json_mode="file",
                    codex_process_pid=os.getpid(),
                )

                status = json.loads((work_dir / ".lgwf" / "codex" / "status.json").read_text(encoding="utf-8"))
                self.assertEqual(status["current_instruction_id"], "propose_requirements_react:codex_prompt")
                self.assertEqual(status["track_files"]["stdout"]["path"], str(stdout_path))
                self.assertEqual(status["output_json"]["path"], str(output_json_path))
                self.assertIsNotNone(status["last_file_update_unix"])

                token_status = codex_command.codex_token_status(
                    work_dir,
                    limit=5,
                    token_max=None,
                    stale_seconds=300,
                )
                self.assertEqual(token_status["token_usage"]["total_tokens"], 0)
                self.assertTrue(token_status["activity"]["stdout_updated"])
                self.assertEqual(token_status["track_files"]["stdout"]["path"], str(stdout_path))
                self.assertEqual(token_status["output_json"]["path"], str(output_json_path))
                self.assertTrue(token_status["process"]["codex"]["alive"])

    def test_missing_output_failure_is_structured_in_track_metadata(self) -> None:
        with ExtractedWheel():
            runner_module = importlib.import_module("lgwf_client.runners.codex_runner.runner")
            json_output = importlib.import_module("lgwf_client.runners.codex_runner.json_output")
            track_store = importlib.import_module("lgwf_client.runners.codex_runner.track_store")

            with tempfile.TemporaryDirectory() as temp:
                work_dir = Path(temp)
                track_dir = work_dir / ".lgwf" / "codex" / "demo-000"
                track_dir.mkdir(parents=True)
                stdout_path = track_dir / "stdout.txt"
                stderr_path = track_dir / "stderr.txt"
                missing_output = work_dir / ".lgwf" / "step_designs_proposal.json"
                stdout_path.write_text("final response without file\n", encoding="utf-8")
                stderr_path.write_text("warning line\n", encoding="utf-8")
                instruction = {"id": "design_steps_react:codex_prompt", "capability": "exec.codex_prompt"}
                track_store.write_track_start(
                    track_dir,
                    instruction,
                    work_dir,
                    ["codex", "exec", "-"],
                    "prompt",
                    "exec",
                    None,
                    [],
                    [],
                    [],
                    missing_output,
                    "file",
                    None,
                )

                exc = json_output.MissingOutputError(
                    "output_json",
                    missing_output,
                    f"file output JSON was requested, but Codex did not create the file: {missing_output}",
                )
                runner = runner_module.CodexRunner(workspace_root=work_dir)
                failure = runner._output_validation_failure(
                    instruction,
                    track_dir,
                    "output_json",
                    missing_output,
                    stdout_path,
                    stderr_path,
                    exc,
                )
                track_store.write_track_finish(
                    track_dir,
                    instruction,
                    work_dir,
                    "exec",
                    1,
                    timed_out=False,
                    runner_error_type=failure["reason"],
                    runner_error_message=failure["message"],
                    failure=failure,
                )

                metadata = json.loads((track_dir / "metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(metadata["runner_error_type"], "missing_output_json")
                self.assertEqual(metadata["failure"]["missing_file"], str(missing_output))
                self.assertEqual(metadata["failure"]["node"], "design_steps_react:codex_prompt")
                self.assertEqual(metadata["failure"]["track_dir"], str(track_dir))
                self.assertIn("final response without file", metadata["failure"]["stdout_tail"])
                self.assertIn("warning line", metadata["failure"]["stderr_tail"])


if __name__ == "__main__":
    unittest.main()
