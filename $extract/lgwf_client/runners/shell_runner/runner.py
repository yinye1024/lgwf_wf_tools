import pathlib
from typing import Any

import lgwf_client.process_execution as process_execution_module
import lgwf_client.resource_refs as resource_refs_module
import lgwf_client.types as client_types


class ShellRunner:
    instruction_type: client_types.InstructionType = "shell"

    def __init__(
        self,
        workflow_root: str | pathlib.Path | None = None,
        workspace_root: str | pathlib.Path | None = None,
    ) -> None:
        self._roots = resource_refs_module.ResourceRoots(
            workflow_root=workflow_root,
            workspace_root=workspace_root,
        )

    def run(
        self,
        instruction: client_types.Instruction,
    ) -> client_types.ExecutionResult:
        command = instruction["payload"].get("command")
        if not isinstance(command, str) or not command.strip():
            raise ValueError("shell instruction payload requires a non-empty command string.")

        cwd = resource_refs_module.resolve_cwd(
            instruction.get("cwd"),
            self._roots,
        )

        completed = process_execution_module.run_shell(
            command,
            cwd=cwd,
            timeout_seconds=instruction["timeout_seconds"],
        )

        metadata: dict[str, Any] = {
            "command": command,
            "cwd": str(cwd),
            "duration_ms": completed.duration_ms,
        }

        return {
            "instruction_id": instruction["id"],
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "artifacts": [],
            "changed_files": [],
            "metadata": metadata,
        }

