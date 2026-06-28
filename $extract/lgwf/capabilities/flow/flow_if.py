from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.route_keys as route_key_module
import lgwf.capabilities.types as capability_types


class FlowIfCapability:
    name = "flow.if"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        condition = config.get("condition", {})

        def node(state: capability_types.State) -> capability_types.State:
            if not isinstance(condition, dict):
                raise ValueError("flow.if v3 requires condition to be an object.")

            next_state = dict(state)
            result = flow_conditions_module.evaluate(condition, state)
            next_state[route_key_module.route_key_for(node_id)] = "true" if result else "false"
            return next_state

        return node


CAPABILITY = FlowIfCapability()

