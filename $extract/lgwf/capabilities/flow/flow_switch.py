from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.route_keys as route_key_module
import lgwf.capabilities.types as capability_types


class FlowSwitchCapability:
    name = "flow.switch"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        path = config.get("path")
        default = config.get("default", "default")

        def node(state: capability_types.State) -> capability_types.State:
            if not isinstance(path, str) or not path:
                raise ValueError("flow.switch v3 requires a non-empty string path.")
            if not isinstance(default, str) or not default:
                raise ValueError("flow.switch v3 requires default to be a non-empty string when provided.")

            next_state = dict(state)
            value = flow_conditions_module.read_path(state, path)
            if flow_conditions_module.is_empty(value):
                route = default
            else:
                route = str(value)
            next_state[route_key_module.route_key_for(node_id)] = route
            return next_state

        return node


CAPABILITY = FlowSwitchCapability()

