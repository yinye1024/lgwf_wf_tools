from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.route_keys as route_key_module
import lgwf.capabilities.types as capability_types


class FlowGuardCapability:
    name = "flow.guard"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        condition = config.get("condition")
        pass_route = config.get("pass_route", "pass")
        fail_route = config.get("fail_route", "fail")

        def node(state: capability_types.State) -> capability_types.State:
            if not isinstance(condition, dict):
                raise ValueError("flow.guard v3 requires condition to be an object.")
            if not isinstance(pass_route, str) or not pass_route:
                raise ValueError("flow.guard pass_route must be a non-empty string.")
            if not isinstance(fail_route, str) or not fail_route:
                raise ValueError("flow.guard fail_route must be a non-empty string.")

            next_state = dict(state)
            result = flow_conditions_module.evaluate(condition, state)
            next_state[route_key_module.route_key_for(node_id)] = pass_route if result else fail_route
            return next_state

        return node


CAPABILITY = FlowGuardCapability()

