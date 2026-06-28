from collections.abc import Awaitable, Callable
from typing import Any, Protocol


State = dict[str, Any]
NodeCallable = Callable[[State], State] | Callable[[State], Awaitable[State]]


class Capability(Protocol):
    name: str

    def create_node(self, node_id: str, config: dict[str, Any]) -> NodeCallable:
        ...

