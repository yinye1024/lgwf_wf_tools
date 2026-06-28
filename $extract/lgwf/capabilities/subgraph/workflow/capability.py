from typing import Any

import lgwf.capabilities.types as capability_types


class SubgraphWorkflowCapability:
    name = "subgraph.workflow"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        workflow = config.get("workflow")
        if not isinstance(workflow, dict):
            raise ValueError(f"Subgraph '{node_id}' requires a workflow object.")

        import lgwf.compiler.dsl as compiler_module

        compiler_module.validate_dsl(workflow)
        graph = compiler_module.compile_dsl(workflow)

        def node(state: capability_types.State) -> capability_types.State:
            return graph.invoke(state)

        return node


CAPABILITY = SubgraphWorkflowCapability()
