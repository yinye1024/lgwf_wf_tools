from typing import Any

import lgwf.capabilities.policy.registry as policy_registry_module


SUBGRAPH_CAPABILITY_PREFIX = "subgraph."


def validate_node(
    node_id: str,
    subgraph_node_name: str,
    subgraph_node: Any,
    *,
    allow_nested_capabilities: set[str] | None = None,
) -> dict[str, Any]:
    if not isinstance(subgraph_node, dict):
        raise ValueError(f"Subgraph '{node_id}' requires object node '{subgraph_node_name}'.")

    capability = subgraph_node.get("capability")
    if not isinstance(capability, str) or not capability:
        raise ValueError(f"Subgraph '{node_id}' node '{subgraph_node_name}' must include a non-empty capability.")
    allowed_nested = allow_nested_capabilities or set()
    if capability.startswith(SUBGRAPH_CAPABILITY_PREFIX) and capability not in allowed_nested:
        raise ValueError(f"Subgraph '{node_id}' node '{subgraph_node_name}' cannot use nested subgraph capability.")

    config = subgraph_node.get("config", {})
    if config is not None and not isinstance(config, dict):
        raise ValueError(f"Subgraph '{node_id}' node '{subgraph_node_name}' config must be an object when provided.")

    policies = subgraph_node.get("policies", [])
    if not isinstance(policies, list):
        raise ValueError(f"Subgraph '{node_id}' node '{subgraph_node_name}' policies must be a list when provided.")
    for policy in policies:
        if not isinstance(policy, dict):
            raise ValueError(f"Subgraph '{node_id}' node '{subgraph_node_name}' policies must contain objects.")

    if "routes" in subgraph_node or "edges" in subgraph_node:
        raise ValueError(f"Subgraph '{node_id}' node '{subgraph_node_name}' cannot define edges or routes.")

    return subgraph_node


def ensure_capability(node_id: str, subgraph_node_name: str, capability: str) -> None:
    import lgwf.capabilities.registry as registry_module

    if not registry_module.has_capability(capability):
        raise ValueError(f"Subgraph '{node_id}' node '{subgraph_node_name}' has unknown capability: {capability}")


def policy_kwargs(node_id: str, subgraph_node_name: str, subgraph_node: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for policy in subgraph_node.get("policies", []):
        policy_capability = policy.get("capability")
        if not isinstance(policy_capability, str) or not policy_capability:
            raise ValueError(
                f"Subgraph '{node_id}' node '{subgraph_node_name}' policy must include a non-empty capability."
            )
        if not policy_registry_module.has_policy(policy_capability):
            raise ValueError(f"Subgraph '{node_id}' node '{subgraph_node_name}' has unknown policy: {policy_capability}")

        policy_config = policy.get("config", {})
        if policy_config is not None and not isinstance(policy_config, dict):
            raise ValueError(
                f"Subgraph '{node_id}' node '{subgraph_node_name}' policy config must be an object when provided."
            )

        next_kwargs = policy_registry_module.create_kwargs(policy_capability, policy_config)
        duplicate_keys = set(result).intersection(next_kwargs)
        if duplicate_keys:
            keys = ", ".join(sorted(duplicate_keys))
            raise ValueError(
                f"Duplicate policy lowering kwargs for subgraph '{node_id}' node '{subgraph_node_name}': {keys}"
            )
        result.update(next_kwargs)

    return result

