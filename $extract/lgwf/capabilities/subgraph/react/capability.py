from typing import Any

from langgraph.graph import StateGraph

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.route_keys as route_key_module
import lgwf.capabilities.subgraph.node as subgraph_node_module
import lgwf.capabilities.types as capability_types
import lgwf.human_approval as human_approval_module
import lgwf.progress as progress_module
import lgwf.runtime_context as runtime_context_module


SLOTS = ("reason", "act", "observe", "decide")
CONTINUE_ROUTE = "continue"
EXIT_ROUTE = "exit"


class SubgraphReactCapability:
    name = "subgraph.react"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        max_steps = self._validate_max_steps(node_id, config)
        slots = self._validate_slots(node_id, config)
        spec_ref = self._validate_spec_ref(node_id, config)
        on_max = self._validate_on_max(node_id, config)
        graph = self._compile_slots(node_id, slots, max_steps, spec_ref, on_max)

        def node(state: capability_types.State) -> capability_types.State:
            return graph.invoke(state)

        return node

    def _validate_max_steps(self, node_id: str, config: dict[str, Any]) -> int:
        max_steps = config.get("max_steps", 5)
        if not isinstance(max_steps, int) or max_steps < 1:
            raise ValueError(f"Subgraph '{node_id}' requires max_steps to be a positive integer.")
        return max_steps

    def _validate_slots(self, node_id: str, config: dict[str, Any]) -> dict[str, dict[str, Any]]:
        slots: dict[str, dict[str, Any]] = {}
        for slot_name in SLOTS:
            slot = config.get(slot_name)
            slots[slot_name] = subgraph_node_module.validate_node(node_id, slot_name, slot)

        return slots

    def _validate_spec_ref(self, node_id: str, config: dict[str, Any]) -> dict[str, Any] | None:
        spec_ref = config.get("spec_ref")
        if spec_ref is None:
            return None
        if not isinstance(spec_ref, dict):
            raise ValueError(f"Subgraph '{node_id}' spec_ref must be an object when provided.")
        path = spec_ref.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"Subgraph '{node_id}' spec_ref.path must be a non-empty string.")
        return dict(spec_ref)

    def _validate_on_max(self, node_id: str, config: dict[str, Any]) -> dict[str, Any] | None:
        on_max = config.get("on_max")
        if on_max is None:
            return None
        if not isinstance(on_max, dict):
            raise ValueError(f"Subgraph '{node_id}' on_max config must be an object when provided.")
        if on_max.get("type") != "human_approval":
            raise ValueError(f"Subgraph '{node_id}' on_max.type must be human_approval.")

        prompt = on_max.get("prompt")
        context_path = on_max.get("context_path")
        approved_value_path = on_max.get("approved_value_path")
        result_path = on_max.get("result_path", f"react.{node_id}.on_max_approval")
        status_path = on_max.get("status_path", f"react.{node_id}.status")
        extra_max_steps = on_max.get("extra_max_steps")
        timeout_seconds = on_max.get("timeout_seconds")
        poll_interval_seconds = on_max.get("poll_interval_seconds", 1)

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Subgraph '{node_id}' on_max.prompt must be a non-empty string.")
        if not isinstance(context_path, str) or not context_path:
            raise ValueError(f"Subgraph '{node_id}' on_max.context_path must be a non-empty string.")
        if not isinstance(approved_value_path, str) or not approved_value_path:
            raise ValueError(f"Subgraph '{node_id}' on_max.approved_value_path must be a non-empty string.")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError(f"Subgraph '{node_id}' on_max.result_path must be a non-empty string.")
        if not isinstance(status_path, str) or not status_path:
            raise ValueError(f"Subgraph '{node_id}' on_max.status_path must be a non-empty string.")
        if not isinstance(extra_max_steps, int) or extra_max_steps < 1:
            raise ValueError(f"Subgraph '{node_id}' on_max.extra_max_steps must be a positive integer.")
        if timeout_seconds is not None and (
            not isinstance(timeout_seconds, int | float) or timeout_seconds <= 0
        ):
            raise ValueError(f"Subgraph '{node_id}' on_max.timeout_seconds must be a positive number or null.")
        if not isinstance(poll_interval_seconds, int | float) or poll_interval_seconds <= 0:
            raise ValueError(f"Subgraph '{node_id}' on_max.poll_interval_seconds must be a positive number.")

        return {
            "prompt": prompt,
            "context_path": context_path,
            "approved_value_path": approved_value_path,
            "result_path": result_path,
            "status_path": status_path,
            "extra_max_steps": extra_max_steps,
            "timeout_seconds": timeout_seconds,
            "poll_interval_seconds": poll_interval_seconds,
        }

    def _compile_slots(
        self,
        node_id: str,
        slots: dict[str, dict[str, Any]],
        max_steps: int,
        spec_ref: dict[str, Any] | None,
        on_max: dict[str, Any] | None,
    ):
        import lgwf.capabilities.registry as registry_module

        tick_node = self._internal_id(node_id, "tick")
        reason_node = self._internal_id(node_id, "reason")
        act_node = self._internal_id(node_id, "act")
        observe_node = self._internal_id(node_id, "observe")
        decide_node = self._internal_id(node_id, "decide")
        enforce_limit_node = self._internal_id(node_id, "enforce_limit")
        route_next_node = self._internal_id(node_id, "route_next")
        cleanup_node = self._internal_id(node_id, "cleanup")

        builder = StateGraph(dict)
        builder.add_node(tick_node, self._tick_node(node_id))
        builder.add_node(enforce_limit_node, self._enforce_limit_node(node_id, max_steps, on_max))
        builder.add_node(route_next_node, self._route_next_node(route_next_node))
        builder.add_node(cleanup_node, self._cleanup_node(node_id, route_next_node))

        slot_nodes = {
            "reason": reason_node,
            "act": act_node,
            "observe": observe_node,
            "decide": decide_node,
        }
        for slot_name, slot_node in slot_nodes.items():
            slot = slots[slot_name]
            capability = slot["capability"]
            subgraph_node_module.ensure_capability(node_id, slot_name, capability)
            slot_config = dict(slot.get("config", {}))
            if spec_ref is not None and slot_name in {"reason", "act", "observe"}:
                slot_config["spec_ref"] = dict(spec_ref)

            builder.add_node(
                slot_node,
                progress_module.wrap_node(
                    slot_node,
                    capability,
                    registry_module.create_node(capability, slot_node, slot_config),
                ),
                **subgraph_node_module.policy_kwargs(node_id, slot_name, slot),
            )

        builder.set_entry_point(tick_node)
        builder.add_edge(tick_node, reason_node)
        builder.add_edge(reason_node, act_node)
        builder.add_edge(act_node, observe_node)
        builder.add_edge(observe_node, decide_node)
        builder.add_edge(decide_node, enforce_limit_node)
        builder.add_edge(enforce_limit_node, route_next_node)
        builder.add_conditional_edges(
            route_next_node,
            self._route_reader(route_next_node),
            {
                CONTINUE_ROUTE: tick_node,
                EXIT_ROUTE: cleanup_node,
            },
        )

        return builder.compile()

    def _tick_node(self, node_id: str) -> capability_types.NodeCallable:
        step_key = self._step_key(node_id)

        def node(state: capability_types.State) -> capability_types.State:
            next_state = dict(state)
            step = next_state.get(step_key, 0)
            if not isinstance(step, int):
                raise ValueError(f"Subgraph '{node_id}' internal step counter must be an integer.")
            next_state[step_key] = step + 1
            next_state.pop("next", None)
            return next_state

        return node

    def _enforce_limit_node(
        self,
        node_id: str,
        max_steps: int,
        on_max: dict[str, Any] | None,
    ) -> capability_types.NodeCallable:
        step_key = self._step_key(node_id)
        continuations_key = self._continuations_key(node_id)

        def node(state: capability_types.State) -> capability_types.State:
            next_state = dict(state)
            step = next_state.get(step_key, 0)
            if not isinstance(step, int):
                raise ValueError(f"Subgraph '{node_id}' internal step counter must be an integer.")
            continuations = next_state.get(continuations_key, 0)
            if not isinstance(continuations, int):
                raise ValueError(f"Subgraph '{node_id}' internal continuation counter must be an integer.")
            if on_max is not None and next_state.get("next") != CONTINUE_ROUTE:
                return self._write_status(
                    next_state,
                    on_max,
                    exit_reason="decide_exit",
                    rounds=step,
                    continuations=continuations,
                    max_steps=max_steps,
                    last_next=next_state.get("next"),
                )
            current_limit = max_steps + continuations * (on_max["extra_max_steps"] if on_max is not None else 0)
            if step >= current_limit and next_state.get("next") == CONTINUE_ROUTE:
                if on_max is not None:
                    return self._handle_on_max_ask(
                        node_id,
                        next_state,
                        on_max,
                        step_key=step_key,
                        continuations_key=continuations_key,
                        max_steps=max_steps,
                    )
                next_state["next"] = EXIT_ROUTE
            return next_state

        return node

    def _handle_on_max_ask(
        self,
        node_id: str,
        state: capability_types.State,
        on_max: dict[str, Any],
        *,
        step_key: str,
        continuations_key: str,
        max_steps: int,
    ) -> capability_types.State:
        workspace_root = runtime_context_module.get_workspace_root()
        if workspace_root is None:
            raise RuntimeError("subgraph.react on_max human approval requires a runtime workspace root.")

        context = flow_conditions_module.read_path(state, on_max["context_path"])
        request = human_approval_module.create_request(
            workspace_root=workspace_root,
            prompt=on_max["prompt"],
            context=context,
        )
        progress_module.emit(
            f"[workflow] human approval pending request_id={request['request_id']}"
        )
        response = human_approval_module.wait_for_response(
            workspace_root=workspace_root,
            request_id=request["request_id"],
            timeout_seconds=None if on_max["timeout_seconds"] is None else float(on_max["timeout_seconds"]),
            poll_interval_seconds=float(on_max["poll_interval_seconds"]),
        )

        next_state = dict(state)
        result = {
            "request_id": request["request_id"],
            "decision": response["decision"],
            "comment": response.get("comment", ""),
        }
        if "value" in response:
            result["value"] = response["value"]
        next_state = flow_conditions_module.write_path(next_state, on_max["result_path"], result)

        step = next_state.get(step_key, 0)
        continuations = next_state.get(continuations_key, 0)
        if not isinstance(step, int):
            raise ValueError(f"Subgraph '{node_id}' internal step counter must be an integer.")
        if not isinstance(continuations, int):
            raise ValueError(f"Subgraph '{node_id}' internal continuation counter must be an integer.")

        if response["decision"] == "approve":
            next_state = flow_conditions_module.write_path(
                next_state,
                on_max["approved_value_path"],
                response["value"],
            )
            continuations += 1
            next_state[continuations_key] = continuations
            return self._write_status(
                next_state,
                on_max,
                exit_reason="max_steps_continue",
                rounds=step,
                continuations=continuations,
                max_steps=max_steps,
                last_next=CONTINUE_ROUTE,
            )

        next_state["next"] = EXIT_ROUTE
        return self._write_status(
            next_state,
            on_max,
            exit_reason="max_steps_stop",
            rounds=step,
            continuations=continuations,
            max_steps=max_steps,
            last_next=CONTINUE_ROUTE,
        )

    def _write_status(
        self,
        state: capability_types.State,
        on_max: dict[str, Any],
        *,
        exit_reason: str,
        rounds: int,
        continuations: int,
        max_steps: int,
        last_next: Any,
    ) -> capability_types.State:
        status = {
            "exit_reason": exit_reason,
            "rounds": rounds,
            "continuations": continuations,
            "max_steps": max_steps,
            "extra_max_steps": on_max["extra_max_steps"],
            "last_next": last_next,
        }
        return flow_conditions_module.write_path(state, on_max["status_path"], status)

    def _route_next_node(self, route_next_node: str) -> capability_types.NodeCallable:
        route_key = route_key_module.route_key_for(route_next_node)

        def node(state: capability_types.State) -> capability_types.State:
            next_state = dict(state)
            next_value = next_state.get("next")
            if next_value == CONTINUE_ROUTE:
                route = CONTINUE_ROUTE
            else:
                route = EXIT_ROUTE
            next_state[route_key] = route
            return next_state

        return node

    def _cleanup_node(self, node_id: str, route_next_node: str) -> capability_types.NodeCallable:
        step_key = self._step_key(node_id)
        continuations_key = self._continuations_key(node_id)
        route_key = route_key_module.route_key_for(route_next_node)

        def node(state: capability_types.State) -> capability_types.State:
            next_state = dict(state)
            next_state.pop(step_key, None)
            next_state.pop(continuations_key, None)
            next_state.pop(route_key, None)
            return next_state

        return node

    def _route_reader(self, route_next_node: str):
        route_key = route_key_module.route_key_for(route_next_node)

        def read_route(state: capability_types.State) -> str:
            route = state.get(route_key)
            if route not in {CONTINUE_ROUTE, EXIT_ROUTE}:
                return EXIT_ROUTE
            return route

        return read_route

    def _internal_id(self, node_id: str, name: str) -> str:
        return f"{node_id}__{name}"

    def _step_key(self, node_id: str) -> str:
        return f"__react__{node_id}__step"

    def _continuations_key(self, node_id: str) -> str:
        return f"__react__{node_id}__continuations"


CAPABILITY = SubgraphReactCapability()

