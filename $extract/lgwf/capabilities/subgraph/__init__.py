"""subgraph.* capability packages."""

import lgwf.capabilities.subgraph.agent_loop as agent_loop_module
import lgwf.capabilities.subgraph.parallel as parallel_module
import lgwf.capabilities.subgraph.react as react_module
import lgwf.capabilities.subgraph.validation_sandbox as validation_sandbox_module
import lgwf.capabilities.subgraph.waterfall as waterfall_module
import lgwf.capabilities.subgraph.workflow as workflow_module


def register_into(registry_module) -> None:
    agent_loop_module.register_into(registry_module)
    parallel_module.register_into(registry_module)
    react_module.register_into(registry_module)
    validation_sandbox_module.register_into(registry_module)
    waterfall_module.register_into(registry_module)
    workflow_module.register_into(registry_module)

