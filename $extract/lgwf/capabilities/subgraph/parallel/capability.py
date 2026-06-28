import contextvars
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langgraph.graph import StateGraph

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.subgraph.node as subgraph_node_module
import lgwf.capabilities.types as capability_types
import lgwf.progress as progress_module


class SubgraphParallelCapability:
    name = "subgraph.parallel"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        steps = self._validate_steps(node_id, config)
        max_concurrency = self._validate_max_concurrency(node_id, config, len(steps))
        fail_strategy = self._validate_fail_strategy(node_id, config)
        step_graphs = {
            step["id"]: self._compile_step(node_id, step)
            for step in steps
        }

        def node(state: capability_types.State) -> capability_types.State:
            results: dict[str, Any] = {}
            with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
                futures = {
                    executor.submit(
                        contextvars.copy_context().run,
                        step_graphs[step["id"]].invoke,
                        dict(state),
                    ): step
                    for step in steps
                }
                for future in as_completed(futures):
                    step = futures[future]
                    try:
                        step_state = future.result()
                        output_path = step["output_path"]
                        if not self._path_exists(step_state, output_path):
                            raise ValueError(
                                f"Subgraph '{node_id}' step '{step['id']}' output_path is missing: {output_path}"
                            )
                        output = flow_conditions_module.read_path(step_state, output_path)
                    except Exception as exc:
                        if fail_strategy == "fail_fast":
                            raise
                        results[step["result_path"]] = {
                            "status": "failed",
                            "error_type": type(exc).__name__,
                            "message": str(exc),
                        }
                    else:
                        if fail_strategy == "collect":
                            results[step["result_path"]] = {
                                "status": "completed",
                                "output": output,
                            }
                        else:
                            results[step["result_path"]] = output

            next_state = dict(state)
            for result_path, value in results.items():
                next_state = flow_conditions_module.write_path(next_state, result_path, value)
            return next_state

        return node

    def _validate_steps(self, node_id: str, config: dict[str, Any]) -> list[dict[str, Any]]:
        steps = config.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"Subgraph '{node_id}' requires a non-empty steps list.")

        step_ids: set[str] = set()
        result_paths: set[str] = set()
        validated_steps: list[dict[str, Any]] = []

        for step in steps:
            if not isinstance(step, dict):
                raise ValueError(f"Subgraph '{node_id}' steps must contain objects.")

            step_id = step.get("id")
            if not isinstance(step_id, str) or not step_id:
                raise ValueError(f"Subgraph '{node_id}' step must include a non-empty id.")
            if step_id in step_ids:
                raise ValueError(f"Subgraph '{node_id}' has duplicate step id: {step_id}")
            step_ids.add(step_id)

            result_path = step.get("result_path")
            if not isinstance(result_path, str) or not result_path:
                raise ValueError(f"Subgraph '{node_id}' step '{step_id}' must include a non-empty result_path.")
            if result_path in result_paths:
                raise ValueError(f"Subgraph '{node_id}' has duplicate result_path: {result_path}")
            result_paths.add(result_path)

            output_path = step.get("output_path", "output")
            if not isinstance(output_path, str) or not output_path:
                raise ValueError(f"Subgraph '{node_id}' step '{step_id}' output_path must be a non-empty string.")

            self._validate_step_node(node_id, step_id, step)
            validated_step = dict(step)
            validated_step["output_path"] = output_path
            validated_steps.append(validated_step)

        return validated_steps

    def _validate_step_node(self, node_id: str, step_id: str, step: dict[str, Any]) -> None:
        capability = step.get("capability")
        if not isinstance(capability, str) or not capability:
            raise ValueError(f"Subgraph '{node_id}' step '{step_id}' must include a non-empty capability.")

        config = step.get("config", {})
        if config is not None and not isinstance(config, dict):
            raise ValueError(f"Subgraph '{node_id}' step '{step_id}' config must be an object when provided.")

        policies = step.get("policies", [])
        if not isinstance(policies, list):
            raise ValueError(f"Subgraph '{node_id}' step '{step_id}' policies must be a list when provided.")
        for policy in policies:
            if not isinstance(policy, dict):
                raise ValueError(f"Subgraph '{node_id}' step '{step_id}' policies must contain objects.")

        if "routes" in step or "edges" in step:
            raise ValueError(f"Subgraph '{node_id}' step '{step_id}' cannot define edges or routes.")

        subgraph_node_module.ensure_capability(node_id, step_id, capability)
        subgraph_node_module.policy_kwargs(node_id, step_id, step)

    def _validate_max_concurrency(self, node_id: str, config: dict[str, Any], step_count: int) -> int:
        max_concurrency = config.get("max_concurrency", step_count)
        if not isinstance(max_concurrency, int) or max_concurrency < 1:
            raise ValueError(f"Subgraph '{node_id}' max_concurrency must be a positive integer.")
        return min(max_concurrency, step_count)

    def _validate_fail_strategy(self, node_id: str, config: dict[str, Any]) -> str:
        fail_strategy = config.get("fail_strategy", "fail_fast")
        if fail_strategy not in {"fail_fast", "collect"}:
            raise ValueError(f"Subgraph '{node_id}' fail_strategy must be fail_fast or collect.")
        return fail_strategy

    def _compile_step(self, node_id: str, step: dict[str, Any]):
        import lgwf.capabilities.registry as registry_module

        internal_step_id = f"{node_id}__{step['id']}"
        capability = step["capability"]

        builder = StateGraph(dict)
        builder.add_node(
            internal_step_id,
            progress_module.wrap_node(
                internal_step_id,
                capability,
                registry_module.create_node(capability, internal_step_id, step.get("config", {})),
            ),
            **subgraph_node_module.policy_kwargs(node_id, step["id"], step),
        )
        builder.set_entry_point(internal_step_id)
        return builder.compile()

    def _path_exists(self, state: capability_types.State, path: str) -> bool:
        current: Any = state
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return False
            current = current[part]
        return True


CAPABILITY = SubgraphParallelCapability()
