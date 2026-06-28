from typing import Any

import lgwf.capabilities.exec.exec_state as exec_state_module
import lgwf.capabilities.types as capability_types


class ExecEchoCapability:
    name = "exec.echo"

    def create_node(self, _node_id: str, _config: dict[str, Any]) -> capability_types.NodeCallable:
        def node(state: capability_types.State) -> capability_types.State:
            next_state = exec_state_module.public_state(state)
            user_input = state.get("input", "")
            next_state["output"] = f"LangGraph DSL runtime received: {user_input}"
            return next_state

        return node


CAPABILITY = ExecEchoCapability()

