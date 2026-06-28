from typing import Any

from langgraph.graph import StateGraph

import lgwf.capabilities.subgraph.node as subgraph_node_module
import lgwf.capabilities.types as capability_types
import lgwf.progress as progress_module


class SubgraphWaterfallCapability:
    name = "subgraph.waterfall"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        steps = self._validate_steps(node_id, config)
        graph = self._compile_steps(node_id, steps)

        def node(state: capability_types.State) -> capability_types.State:
            return graph.invoke(state)

        return node

    def _validate_steps(self, node_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        steps = config.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"Subgraph '{node_id}' requires a non-empty steps list.")

        step_ids: set[str] = set()
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError(f"Subgraph '{node_id}' steps must contain objects.")

            step_id = step.get("id")
            if not isinstance(step_id, str) or not step_id:
                raise ValueError(f"Subgraph '{node_id}' step must include a non-empty id.")
            if step_id in step_ids:
                raise ValueError(f"Subgraph '{node_id}' has duplicate step id: {step_id}")
            step_ids.add(step_id)
            subgraph_node_module.validate_node(node_id, step_id, step)

        return steps

    def _compile_steps(self, node_id: str, steps: list[dict[str, Any]]):
        import lgwf.capabilities.registry as registry_module

        builder = StateGraph(dict)
        previous_step_id: str | None = None

        for step in steps:
            step_id = step["id"]
            capability = step["capability"]
            subgraph_node_module.ensure_capability(node_id, step_id, capability)

            builder.add_node(
                step_id,
                progress_module.wrap_node(
                    step_id,
                    capability,
                    registry_module.create_node(capability, step_id, step.get("config", {})),
                ),
                **subgraph_node_module.policy_kwargs(node_id, step_id, step),
            )

            if previous_step_id is None:
                builder.set_entry_point(step_id)
            else:
                builder.add_edge(previous_step_id, step_id)
            previous_step_id = step_id

        return builder.compile()


CAPABILITY = SubgraphWaterfallCapability()

