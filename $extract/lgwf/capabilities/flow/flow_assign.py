from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types


class FlowAssignCapability:
    name = "flow.assign"

    def create_node(self, _node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        assignments = config.get("assignments")

        def node(state: capability_types.State) -> capability_types.State:
            if not isinstance(assignments, dict) or not assignments:
                raise ValueError("flow.assign v3 requires a non-empty assignments object.")

            next_state = dict(state)
            for path, value in assignments.items():
                if not isinstance(path, str) or not path:
                    raise ValueError("flow.assign assignment keys must be non-empty string paths.")
                next_state = flow_conditions_module.write_path(next_state, path, value)
            return next_state

        return node


CAPABILITY = FlowAssignCapability()

