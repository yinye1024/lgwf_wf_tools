from typing import Any

from langgraph.graph import StateGraph

import lgwf.capabilities.registry as registry_module
import lgwf.capabilities.policy.registry as policy_registry_module
import lgwf.compiler.lowering as lowering_module


Dsl = dict[str, Any]


class DSLValidationError(ValueError):
    """Raised when a workflow DSL document is invalid."""


def validate_dsl(dsl: Dsl) -> None:
    nodes = dsl.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise DSLValidationError("DSL must include a non-empty 'nodes' list.")

    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise DSLValidationError("Each node must be an object.")

        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise DSLValidationError("Each node must include a non-empty string 'id'.")
        if node_id in node_ids:
            raise DSLValidationError(f"Duplicate node id: {node_id}")
        node_ids.add(node_id)

        capability = node.get("capability")
        if not isinstance(capability, str) or not capability:
            raise DSLValidationError(f"Node '{node_id}' must include a non-empty string capability.")
        if not registry_module.has_capability(capability):
            raise DSLValidationError(f"Unknown capability: {capability}")

        config = node.get("config", {})
        if config is not None and not isinstance(config, dict):
            raise DSLValidationError(f"Node '{node_id}' config must be an object when provided.")

        policies = node.get("policies", [])
        if not isinstance(policies, list):
            raise DSLValidationError(f"Node '{node_id}' policies must be a list when provided.")
        for policy in policies:
            if not isinstance(policy, dict):
                raise DSLValidationError(f"Node '{node_id}' policies must contain objects.")

            policy_capability = policy.get("capability")
            if not isinstance(policy_capability, str) or not policy_capability:
                raise DSLValidationError(f"Node '{node_id}' policy must include a non-empty capability.")
            if not policy_registry_module.has_policy(policy_capability):
                raise DSLValidationError(f"Unknown policy: {policy_capability}")

            policy_config = policy.get("config", {})
            if policy_config is not None and not isinstance(policy_config, dict):
                raise DSLValidationError(f"Node '{node_id}' policy config must be an object when provided.")

    entry_point = dsl.get("entry_point")
    if not isinstance(entry_point, str) or not entry_point:
        raise DSLValidationError("DSL must include a non-empty string 'entry_point'.")
    if entry_point not in node_ids:
        raise DSLValidationError(f"Unknown entry_point: {entry_point}")

    edges = dsl.get("edges", [])
    if not isinstance(edges, list):
        raise DSLValidationError("'edges' must be a list when provided.")
    for edge in edges:
        if not isinstance(edge, list) or len(edge) != 2:
            raise DSLValidationError("Each edge must be a two-item list: ['from', 'to'].")
        src, dst = edge
        if not isinstance(src, str) or src not in node_ids:
            raise DSLValidationError(f"Unknown edge source node: {src}")
        if not isinstance(dst, str) or dst not in node_ids:
            raise DSLValidationError(f"Unknown edge target node: {dst}")

    routes = dsl.get("routes", [])
    if not isinstance(routes, list):
        raise DSLValidationError("'routes' must be a list when provided.")
    for route in routes:
        if not isinstance(route, dict):
            raise DSLValidationError("Each route must be an object.")

        source = route.get("from")
        if not isinstance(source, str) or source not in node_ids:
            raise DSLValidationError(f"Unknown route source node: {source}")

        branches = route.get("branches")
        if not isinstance(branches, dict) or not branches:
            raise DSLValidationError(f"Route from '{source}' must include non-empty branches.")
        for branch_key, target in branches.items():
            if not isinstance(branch_key, str) or not branch_key:
                raise DSLValidationError(f"Route from '{source}' includes an invalid branch key.")
            if not isinstance(target, str) or target not in node_ids:
                raise DSLValidationError(f"Unknown route target node: {target}")


def compile_dsl(dsl: Dsl):
    validate_dsl(dsl)

    builder = StateGraph(dict)
    lowering_module.add_nodes(builder, dsl)
    lowering_module.add_edges(builder, dsl)
    lowering_module.add_routes(builder, dsl)
    builder.set_entry_point(dsl["entry_point"])
    return builder.compile()

