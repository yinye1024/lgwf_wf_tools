import json
import pathlib
import sys
import tempfile

import lgwf_client.process_execution as process_execution_module
import lgwf_client.types as client_types


class ToolRunner:
    instruction_type: client_types.InstructionType = "tool"

    def __init__(self, workspace_root: str | pathlib.Path | None = None) -> None:
        self._workspace_root = pathlib.Path(workspace_root).resolve() if workspace_root is not None else None

    def run(self, instruction: client_types.Instruction) -> client_types.ExecutionResult:
        if self._workspace_root is None:
            raise ValueError("ToolRunner requires a workspace_root.")
        payload = instruction.get("payload", {})
        tool = payload.get("tool")
        options = payload.get("options", {})
        with tempfile.TemporaryDirectory(prefix="lgwf-tool-") as temp_dir:
            request_path = pathlib.Path(temp_dir) / "request.json"
            request_path.write_text(
                json.dumps(
                    {
                        "tool": tool,
                        "options": options,
                        "workspace_root": str(self._workspace_root),
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            command = [
                sys.executable,
                "-m",
                "lgwf_client.runners.tool_runner.worker",
                "--request-json",
                str(request_path),
            ]
            completed = process_execution_module.run_command(
                command,
                timeout_seconds=instruction.get("timeout_seconds"),
            )
        if completed.timed_out:
            timeout_seconds = instruction.get("timeout_seconds")
            return {
                "instruction_id": instruction["id"],
                "ok": False,
                "exit_code": -1,
                "stdout": completed.stdout,
                "stderr": f"tool execution timed out after {timeout_seconds} seconds",
                "artifacts": [],
                "changed_files": [],
                "metadata": {
                    "type": "tool",
                    "tool": tool,
                    "workspace_root": str(self._workspace_root),
                    "duration_ms": completed.duration_ms,
                    "timed_out": True,
                },
            }
        envelope = _worker_envelope(completed)
        if not envelope["ok"]:
            message = envelope.get("message", "tool execution failed")
            if envelope.get("error_type") == "ValueError":
                raise ValueError(message)
            raise RuntimeError(message)
        result = envelope["result"]
        return {
            "instruction_id": instruction["id"],
            "ok": True,
            "exit_code": 0,
            "stdout": json.dumps(result, ensure_ascii=False),
            "stderr": "",
            "artifacts": [],
            "changed_files": [],
            "metadata": {
                "type": "tool",
                "tool": tool,
                "workspace_root": str(self._workspace_root),
                "result": result,
                "duration_ms": completed.duration_ms,
                "timed_out": False,
            },
        }


def _worker_envelope(completed: process_execution_module.ProcessResult) -> dict:
    if completed.returncode != 0:
        message = completed.stderr.strip() or f"tool worker exited with code {completed.returncode}"
        raise RuntimeError(message)
    try:
        envelope = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("tool worker returned invalid JSON") from exc
    if not isinstance(envelope, dict) or not isinstance(envelope.get("ok"), bool):
        raise RuntimeError("tool worker returned an invalid response")
    return envelope
