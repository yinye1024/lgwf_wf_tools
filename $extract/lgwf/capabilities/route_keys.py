ROUTE_KEY_PREFIX = "__route__"


def route_key_for(node_id: str) -> str:
    return f"{ROUTE_KEY_PREFIX}{node_id}"


def is_route_key(key: str) -> bool:
    return key.startswith(ROUTE_KEY_PREFIX)

