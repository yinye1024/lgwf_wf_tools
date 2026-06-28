import pathlib

import lgwf_client.python_execution as python_execution_module
import lgwf_client.types as client_types


class PythonRunner:
    instruction_type: client_types.InstructionType = "python"

    def __init__(
        self,
        workflow_root: str | pathlib.Path | None = None,
        workspace_root: str | pathlib.Path | None = None,
    ) -> None:
        self._tool = python_execution_module.PythonExecutionTool(
            workflow_root=workflow_root,
            workspace_root=workspace_root,
        )

    def run(
        self,
        instruction: client_types.Instruction,
    ) -> client_types.ExecutionResult:
        return self._tool.run_instruction(instruction)

