from collections.abc import Callable
from typing import Any

from langgraph.graph import StateGraph

import lgwf.capabilities.registry as registry_module
import lgwf.capabilities.policy.registry as policy_registry_module
import lgwf.capabilities.route_keys as route_key_module
import lgwf.capabilities.types as capability_types
import lgwf.progress as progress_module


Dsl = dict[str, Any]


def _route_reader(node_id: str) -> Callable[[capability_types.State], str]:
    route_key = route_key_module.route_key_for(node_id)

    def read_route(state: capability_types.State) -> str:
        value = state.get(route_key)
        if not isinstance(value, str):
            raise ValueError(f"Route node '{node_id}' did not produce route key '{route_key}'.")
        return value

    return read_route


def add_nodes(builder: StateGraph, dsl: Dsl) -> None:
    for node in dsl["nodes"]:
        node_id = node["id"]
        capability = node["capability"]
        config = node.get("config", {})
        policy_kwargs: dict[str, Any] = {}
        node_wrappers = []

        for policy in node.get("policies", []):
            policy_capability = policy["capability"]
            policy_config = policy.get("config", {})
            next_kwargs = policy_registry_module.create_kwargs(policy_capability, policy_config)
            next_wrappers = next_kwargs.pop("__lgwf_node_wrappers", [])
            node_wrappers.extend(next_wrappers)
            duplicate_keys = set(policy_kwargs).intersection(next_kwargs)
            if duplicate_keys:
                keys = ", ".join(sorted(duplicate_keys))
                raise ValueError(f"Duplicate policy lowering kwargs for node '{node_id}': {keys}")
            policy_kwargs.update(next_kwargs)

        node_callable = registry_module.create_node(capability, node_id, config)
        for wrapper in node_wrappers:
            node_callable = wrapper(node_callable)

        builder.add_node(
            node_id,
            progress_module.wrap_node(
                node_id,
                capability,
                node_callable,
            ),
            **policy_kwargs,
        )


def add_edges(builder: StateGraph, dsl: Dsl) -> None:
    for src, dst in dsl.get("edges", []):
        builder.add_edge(src, dst)


def add_routes(builder: StateGraph, dsl: Dsl) -> None:
    for route in dsl.get("routes", []):
        source = route["from"]
        branches = route["branches"]
        builder.add_conditional_edges(source, _route_reader(source), branches)

