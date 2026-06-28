from typing import Any, Protocol


class MappingContext:
    def __init__(self, entry_point: str) -> None:
        self.entry_point = entry_point
        self.nodes: list[dict] = []
        self.edges: list[list[str]] = []
        self.routes_by_source: dict[str, dict[str, str]] = {}
        self.node_indexes: dict[str, int] = {}

    def add_node(self, node: dict) -> None:
        self.node_indexes[node["id"]] = len(self.nodes)
        self.nodes.append(node)

    def add_edge(self, from_node: str, to_node: str) -> None:
        self.edges.append([from_node, to_node])

    def add_route(self, from_node: str, branches: dict[str, str]) -> None:
        existing = self.routes_by_source.setdefault(from_node, {})
        existing.update(branches)

    def add_policy(self, node_id: str, policy: dict) -> None:
        node = self.nodes[self.node_indexes[node_id]]
        policies = node.setdefault("policies", [])
        policies.append(policy)

    def to_workflow(self) -> dict:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "routes": [
                {"from": source, "branches": branches}
                for source, branches in self.routes_by_source.items()
            ],
            "entry_point": self.entry_point,
        }


class StatementMapping(Protocol):
    def supports(self, statement: Any) -> bool:
        ...

    def lower(self, statement: Any, context: MappingContext) -> None:
        ...
