from typing import Any

import lgwf.capabilities.types as capability_types


def read_path(state: capability_types.State, path: str) -> Any:
    current: Any = state
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def write_path(state: capability_types.State, path: str, value: Any) -> capability_types.State:
    if not isinstance(path, str) or not path:
        raise ValueError("Flow assignment path must be a non-empty string.")

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
            raise ValueError(f"Cannot assign nested path through non-object state field: {part}")
        current[part] = child
        current = child

    current[parts[-1]] = value
    return next_state


def is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def evaluate(condition: dict[str, Any], state: capability_types.State) -> bool:
    path = condition.get("path")
    op = condition.get("op")

    if not isinstance(path, str) or not path:
        raise ValueError("Flow condition requires a non-empty string path.")
    if not isinstance(op, str) or not op:
        raise ValueError("Flow condition requires a non-empty string op.")

    value = read_path(state, path)

    if op == "exists":
        return not is_empty(value)
    if op == "empty":
        return is_empty(value)
    if op == "not_empty":
        return not is_empty(value)
    if op == "equals":
        return value == condition.get("value")
    if op == "not_equals":
        return value != condition.get("value")
    if op == "in":
        candidates = condition.get("values")
        if not isinstance(candidates, list):
            raise ValueError("Flow condition op='in' requires a list values field.")
        return value in candidates

    raise ValueError(f"Unsupported flow condition op: {op}")

