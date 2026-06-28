from typing import Any

import lgwf.capabilities.exec.exec_result as exec_result_module
import lgwf.capabilities.exec.exec_state as exec_state_module
import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types
import lgwf.client_provider as client_provider_module
import lgwf_client.tools.catalog as tool_catalog_module
import lgwf_client.types as client_types


class ExecRunToolCapability:
    name = "exec.run_tool"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        tool = config.get("tool")
        options = config.get("options", {})
        timeout_seconds = config.get("timeout_seconds", 300)
        result_path = config.get("result_path", "last_result")

        tool_catalog_module.validate_public_tool_options(tool, options)
        if timeout_seconds is not None and (
            not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0
        ):
            raise ValueError("exec.run_tool config.timeout_seconds must be a positive integer or null.")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError("exec.run_tool config.result_path must be a non-empty string.")

        def node(state: capability_types.State) -> capability_types.State:
            instruction: client_types.Instruction = {
                "id": f"{node_id}:run_tool",
                "type": "tool",
                "payload": {
                    "tool": tool,
                    "options": options,
                },
                "timeout_seconds": timeout_seconds,
            }
            client = self._client or client_provider_module.get_client()
            result = client.execute(instruction)
            exec_result_module.raise_on_failed_result(self.name, node_id, result)
            next_state = exec_state_module.public_state(state)
            return flow_conditions_module.write_path(next_state, result_path, result)

        return node


CAPABILITY = ExecRunToolCapability()
