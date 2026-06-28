import sys
from typing import Any

import lgwf.capabilities.exec.exec_codex_prompt as exec_codex_prompt_module
import lgwf.capabilities.exec.exec_echo as exec_echo_module
import lgwf.capabilities.exec.exec_inspect_project as exec_inspect_project_module
import lgwf.capabilities.exec.exec_missing_input as exec_missing_input_module
import lgwf.capabilities.exec.exec_run_python as exec_run_python_module
import lgwf.capabilities.exec.exec_run_tool as exec_run_tool_module
import lgwf.capabilities.exec.exec_run_shell as exec_run_shell_module
import lgwf.capabilities.exec.exec_run_tests as exec_run_tests_module
import lgwf.capabilities.flow.flow_assign as flow_assign_module
import lgwf.capabilities.flow.flow_check as flow_check_module
import lgwf.capabilities.flow.flow_guard as flow_guard_module
import lgwf.capabilities.flow.flow_human_approval as flow_human_approval_module
import lgwf.capabilities.flow.flow_if as flow_if_module
import lgwf.capabilities.flow.flow_switch as flow_switch_module
import lgwf.capabilities.subgraph as subgraph_module

import lgwf.capabilities.types as capability_types


_CAPABILITIES: list[capability_types.Capability] = [
    exec_echo_module.CAPABILITY,
    exec_codex_prompt_module.CAPABILITY,
    exec_inspect_project_module.CAPABILITY,
    exec_missing_input_module.CAPABILITY,
    exec_run_python_module.CAPABILITY,
    exec_run_tool_module.CAPABILITY,
    exec_run_shell_module.CAPABILITY,
    exec_run_tests_module.CAPABILITY,
    flow_assign_module.CAPABILITY,
    flow_check_module.CAPABILITY,
    flow_guard_module.CAPABILITY,
    flow_human_approval_module.CAPABILITY,
    flow_if_module.CAPABILITY,
    flow_switch_module.CAPABILITY,
]


REGISTRY: dict[str, capability_types.Capability] = {}


def register(capability: capability_types.Capability) -> None:
    if capability.name in REGISTRY:
        raise ValueError(f"Duplicate capability registration: {capability.name}")
    REGISTRY[capability.name] = capability


for _capability in _CAPABILITIES:
    register(_capability)

subgraph_module.register_into(sys.modules[__name__])


def has_capability(capability: str) -> bool:
    return capability in REGISTRY


def create_node(capability: str, node_id: str, config: dict[str, Any] | None = None) -> capability_types.NodeCallable:
    try:
        entry = REGISTRY[capability]
    except KeyError as exc:
        raise ValueError(f"Unknown capability: {capability}") from exc

    return entry.create_node(node_id, config or {})

