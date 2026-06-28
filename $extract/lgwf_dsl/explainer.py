from typing import Any

import lgwf_client.tools.catalog as tool_catalog_module


class WorkflowExplainer:
    def explain(self, workflow: dict[str, Any]) -> dict[str, Any]:
        return {
            "entry_point": workflow["entry_point"],
            "node_count": len(workflow["nodes"]),
            "nodes": [
                {
                    "id": node["id"],
                    "capability": node["capability"],
                }
                for node in workflow["nodes"]
            ],
            "edges": workflow.get("edges", []),
            "routes": workflow.get("routes", []),
            "route_edges": self._route_edges(workflow),
            "human_approval_nodes": self._human_approval_nodes(workflow),
            "resources": self._resources(workflow),
            "state_paths": self._state_paths(workflow),
            "nested_workflows": self._nested_workflows(workflow),
            "tools": self._tools(workflow),
        }

    def _route_edges(self, workflow: dict[str, Any], prefix: str = "") -> list[dict[str, str]]:
        route_edges: list[dict[str, str]] = []
        for route in workflow.get("routes", []):
            if not isinstance(route, dict):
                continue
            from_node = route.get("from")
            branches = route.get("branches")
            if not isinstance(from_node, str) or not isinstance(branches, dict):
                continue
            for decision, target in branches.items():
                if isinstance(decision, str) and isinstance(target, str):
                    route_edges.append(
                        {
                            "from": self._prefixed_id(prefix, from_node),
                            "to": self._prefixed_id(prefix, target),
                            "decision": decision,
                        }
                    )
        for node in workflow.get("nodes", []):
            if not isinstance(node, dict):
                continue
            config = node.get("config", {})
            if not isinstance(config, dict):
                continue
            child = config.get("workflow")
            if isinstance(child, dict):
                route_edges.extend(self._route_edges(child, self._prefixed_id(prefix, str(node.get("id", "node")))))
        return route_edges

    def _prefixed_id(self, prefix: str, node_id: str) -> str:
        return f"{prefix}.{node_id}" if prefix else node_id

    def _human_approval_nodes(self, workflow: dict[str, Any]) -> list[dict[str, Any]]:
        approvals = []
        for node in workflow["nodes"]:
            config = node.get("config", {})
            if node.get("capability") != "flow.human_approval":
                if node.get("capability") == "subgraph.workflow":
                    child = config.get("workflow")
                    if isinstance(child, dict):
                        for approval in self._human_approval_nodes(child):
                            approvals.append({**approval, "id": f"{node['id']}.{approval['id']}"})
                continue
            approvals.append(
                {
                    "id": node["id"],
                    "context_path": config.get("context_path"),
                    "approved_value_path": config.get("approved_value_path"),
                    "result_path": config.get("result_path"),
                }
            )
        return approvals

    def _resources(self, workflow: dict[str, Any]) -> list[dict[str, Any]]:
        resources = []
        for node in workflow["nodes"]:
            resources.extend(self._node_resources(node["id"], node))
        return resources

    def _node_resources(self, node_id: str, node: dict[str, Any]) -> list[dict[str, Any]]:
        resources = []
        config = node.get("config", {})
        for key in ("prompt_ref", "script_ref", "spec_ref"):
            value = config.get(key)
            if isinstance(value, dict):
                resources.append({"node": node_id, "field": key, **value})
        for context in config.get("context_refs", []):
            if isinstance(context, dict):
                resources.append({"node": node_id, "field": "context_refs", **context})
        if node.get("capability") == "subgraph.react":
            for slot_name in ("reason", "act", "observe", "decide"):
                slot = config.get(slot_name)
                if isinstance(slot, dict):
                    slot_node = {"id": f"{node_id}.{slot_name}", **slot}
                    resources.extend(self._node_resources(slot_node["id"], slot_node))
        if node.get("capability") == "subgraph.parallel":
            for step in config.get("steps", []):
                if isinstance(step, dict):
                    step_node = {"id": f"{node_id}.{step.get('id', 'step')}", **step}
                    resources.extend(self._node_resources(step_node["id"], step_node))
        if node.get("capability") == "subgraph.workflow":
            child = config.get("workflow")
            if isinstance(child, dict):
                for resource in self._resources(child):
                    resources.append({**resource, "node": f"{node_id}.{resource['node']}"})
        return resources

    def _state_paths(self, workflow: dict[str, Any]) -> dict[str, list[str]]:
        reads: set[str] = set()
        writes: set[str] = set()
        for node in workflow["nodes"]:
            self._collect_state_paths(node, reads, writes)
        return {"reads": sorted(reads), "writes": sorted(writes)}

    def _collect_state_paths(self, node: dict[str, Any], reads: set[str], writes: set[str]) -> None:
        config = node.get("config", {})
        for key in ("instruction_path", "result_path", "approved_value_path"):
            value = config.get(key)
            if isinstance(value, str):
                writes.add(value)
        for key in ("context_path", "target_dirs_path", "target_files_path"):
            value = config.get(key)
            if isinstance(value, str):
                reads.add(value)
        if node.get("capability") == "subgraph.react":
            for slot_name in ("reason", "act", "observe", "decide"):
                slot = config.get(slot_name)
                if isinstance(slot, dict):
                    self._collect_state_paths(slot, reads, writes)
        if node.get("capability") == "subgraph.parallel":
            for step in config.get("steps", []):
                if not isinstance(step, dict):
                    continue
                for key in ("output_path", "result_path"):
                    value = step.get(key)
                    if isinstance(value, str):
                        writes.add(value)
                self._collect_state_paths(step, reads, writes)
        if node.get("capability") == "subgraph.workflow":
            child = config.get("workflow")
            if isinstance(child, dict):
                for child_node in child.get("nodes", []):
                    if isinstance(child_node, dict):
                        self._collect_state_paths(child_node, reads, writes)

    def _nested_workflows(self, workflow: dict[str, Any]) -> list[dict[str, Any]]:
        nested = []
        for node in workflow["nodes"]:
            if node.get("capability") != "subgraph.workflow":
                continue
            child = node.get("config", {}).get("workflow")
            if not isinstance(child, dict):
                continue
            nested.append(
                {
                    "id": node["id"],
                    "entry_point": child.get("entry_point"),
                    "node_count": len(child.get("nodes", [])),
                }
            )
            for child_summary in self._nested_workflows(child):
                nested.append({**child_summary, "id": f"{node['id']}.{child_summary['id']}"})
        return nested

    def _tools(self, workflow: dict[str, Any]) -> list[dict[str, Any]]:
        descriptors = tool_catalog_module.tool_descriptors()
        tools: list[dict[str, Any]] = []
        for node in workflow["nodes"]:
            tools.extend(self._node_tools(node["id"], node, descriptors))
        return tools

    def _node_tools(
        self,
        node_id: str,
        node: dict[str, Any],
        descriptors: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        config = node.get("config", {})
        if node.get("capability") == "exec.run_tool":
            tool_name = config.get("tool")
            descriptor = descriptors.get(tool_name, {})
            return [
                {
                    "node": node_id,
                    "tool": tool_name,
                    "options": config.get("options", {}),
                    "result_path": config.get("result_path"),
                    "mutates_files": bool(descriptor.get("mutates_files", False)),
                }
            ]
        tools: list[dict[str, Any]] = []
        if node.get("capability") == "subgraph.react":
            for slot_name in ("reason", "act", "observe", "decide"):
                slot = config.get(slot_name)
                if isinstance(slot, dict):
                    tools.extend(self._node_tools(f"{node_id}.{slot_name}", slot, descriptors))
        elif node.get("capability") == "subgraph.parallel":
            for step in config.get("steps", []):
                if isinstance(step, dict):
                    tools.extend(
                        self._node_tools(
                            f"{node_id}.{step.get('id', 'step')}",
                            step,
                            descriptors,
                        )
                    )
        elif node.get("capability") == "subgraph.workflow":
            child = config.get("workflow")
            if isinstance(child, dict):
                for child_node in child.get("nodes", []):
                    if isinstance(child_node, dict):
                        child_id = child_node.get("id", "node")
                        tools.extend(
                            self._node_tools(
                                f"{node_id}.{child_id}",
                                child_node,
                                descriptors,
                            )
                        )
        return tools
