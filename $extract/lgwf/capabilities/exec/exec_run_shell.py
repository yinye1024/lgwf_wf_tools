from typing import Any

import lgwf.capabilities.exec.exec_state as exec_state_module
import lgwf.capabilities.exec.exec_result as exec_result_module
import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types
import lgwf.client_provider as client_provider_module
import lgwf_client.types as client_types


class ExecRunShellCapability:
    name = "exec.run_shell"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        command = config.get("command")
        cwd = config.get("cwd")
        timeout_seconds = config.get("timeout_seconds", 300)
        instruction_path = config.get("instruction_path", "last_instruction")
        result_path = config.get("result_path", "last_result")

        if not isinstance(command, str) or not command.strip():
            raise ValueError("exec.run_shell requires config.command to be a non-empty string.")
        if cwd is not None and (not isinstance(cwd, str) or not cwd.strip()):
            raise ValueError("exec.run_shell config.cwd must be a non-empty string.")
        if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
            raise ValueError("exec.run_shell config.timeout_seconds must be a positive integer.")
        if not isinstance(instruction_path, str) or not instruction_path:
            raise ValueError("exec.run_shell config.instruction_path must be a non-empty string.")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError("exec.run_shell config.result_path must be a non-empty string.")

        def node(state: capability_types.State) -> capability_types.State:
            instruction: client_types.Instruction = {
                "id": f"{node_id}:run_shell",
                "type": "shell",
                "payload": {
                    "command": command,
                },
                "timeout_seconds": timeout_seconds,
            }
            if cwd is not None:
                instruction["cwd"] = cwd

            client = self._client or client_provider_module.get_client()
            result = client.execute(instruction)
            exec_result_module.raise_on_failed_result(self.name, node_id, result)
            next_state = exec_state_module.public_state(state)
            next_state = flow_conditions_module.write_path(next_state, instruction_path, instruction)
            next_state = flow_conditions_module.write_path(next_state, result_path, result)
            return next_state

        return node


CAPABILITY = ExecRunShellCapability()

