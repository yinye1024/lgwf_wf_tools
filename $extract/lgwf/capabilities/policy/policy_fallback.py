from typing import Any

import inspect
import lgwf.capabilities.types as capability_types
import lgwf.capabilities.policy.types as policy_types


def _write_path(state: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    if not isinstance(path, str) or not path:
        raise ValueError("policy.fallback assignment path must be a non-empty string.")

    parts = path.split(".")
    next_state = dict(state)
    current: dict[str, Any] = next_state

    for part in parts[:-1]:
        existing = current.get(part)
        if existing is None:
            child: dict[str, Any] = {}
        elif isinstance(existing, dict):
            child = dict(existing)
        else:
            raise ValueError(f"Cannot assign nested fallback path through non-object state field: {part}")
        current[part] = child
        current = child

    current[parts[-1]] = value
    return next_state


class PolicyFallbackCapability:
    name = "policy.fallback"

    def create_kwargs(self, config: dict[str, Any]) -> policy_types.PolicyKwargs:
        assignments = config.get("assignments")
        if not isinstance(assignments, dict) or not assignments:
            raise ValueError("policy.fallback requires a non-empty assignments object.")
        for path in assignments:
            if not isinstance(path, str) or not path:
                raise ValueError("policy.fallback assignment keys must be non-empty string paths.")

        def handler(state: dict[str, Any]) -> dict[str, Any]:
            next_state = dict(state)
            for path, value in assignments.items():
                next_state = _write_path(next_state, path, value)
            return next_state

        def wrap_node(node: capability_types.NodeCallable) -> capability_types.NodeCallable:
            if inspect.iscoroutinefunction(node):
                async def async_wrapped(state: capability_types.State) -> capability_types.State:
                    try:
                        return await node(state)
                    except Exception:
                        return handler(state)

                return async_wrapped

            def wrapped(state: capability_types.State) -> capability_types.State:
                try:
                    return node(state)
                except Exception:
                    return handler(state)

            return wrapped

        return {
            "__lgwf_node_wrappers": [wrap_node],
        }


CAPABILITY = PolicyFallbackCapability()

