import json
from pathlib import Path
from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.subgraph.node as subgraph_node_module
import lgwf.capabilities.types as capability_types
import lgwf.client_provider as client_provider_module
import lgwf.progress as progress_module
import lgwf.runtime_context as runtime_context_module
import lgwf_client.client_factory as client_factory_module
import lgwf_client.tools.operations as tool_operations_module


SLOTS = ("observe", "diagnose", "plan", "act", "verify", "decide")
PROMOTE_CATEGORIES = {"continue", "finish"}
CONTROL_POLICIES = {"block", "wait_human"}
MEMORY_CONTEXT_SLOTS = {"observe", "diagnose", "plan", "verify", "decide"}
MEMORY_FAILED_ATTEMPTS_LIMIT = 5
MEMORY_CHANGE_PATH_LIMIT = 20


class SubgraphAgentLoopCapability:
    name = "subgraph.agent_loop"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        loop_config = self._validate_config(node_id, config)
        slot_nodes = self._create_slot_nodes(node_id, loop_config)

        def node(state: capability_types.State) -> capability_types.State:
            return self._run_loop(node_id, loop_config, slot_nodes, state)

        return node

    def _validate_config(self, node_id: str, config: dict[str, Any]) -> dict[str, Any]:
        max_iterations = config.get("max_iterations")
        if not isinstance(max_iterations, int) or max_iterations < 1:
            raise ValueError(f"Subgraph '{node_id}' requires max_iterations to be a positive integer.")
        token_max = config.get("token_max", 1000000)
        if not isinstance(token_max, int) or token_max < 1:
            raise ValueError(f"Subgraph '{node_id}' token_max must be a positive integer.")

        artifacts_path = config.get("artifacts_path")
        if not isinstance(artifacts_path, str) or not artifacts_path:
            raise ValueError(f"Subgraph '{node_id}' requires artifacts_path.")
        self._validate_relative_path(node_id, artifacts_path, "artifacts_path")

        goal = config.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError(f"Subgraph '{node_id}' requires goal.")

        status_path = config.get("status_path", f"agent_loop.{node_id}.status")
        report_path = config.get("report_path", f"agent_loop.{node_id}.report")
        target_dirs_path = config.get("target_dirs_path", "targets.dirs")
        target_files_path = config.get("target_files_path", "targets.files")
        on_max = self._validate_control_policy(node_id, config.get("on_max", "block"), "on_max")
        on_error = self._validate_control_policy(node_id, config.get("on_error", "block"), "on_error")
        for label, value in (
            ("status_path", status_path),
            ("report_path", report_path),
            ("target_dirs_path", target_dirs_path),
            ("target_files_path", target_files_path),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"Subgraph '{node_id}' {label} must be a non-empty string.")

        slots = {}
        for slot_name in SLOTS:
            slot = subgraph_node_module.validate_node(
                node_id,
                slot_name,
                config.get(slot_name),
                allow_nested_capabilities={"subgraph.workflow"},
            )
            capability = slot["capability"]
            subgraph_node_module.ensure_capability(node_id, slot_name, capability)
            slots[slot_name] = slot
        slot_order = self._validate_slot_order(node_id, config.get("slot_order"))

        return {
            "max_iterations": max_iterations,
            "token_max": token_max,
            "artifacts_path": artifacts_path,
            "goal": goal,
            "status_path": status_path,
            "report_path": report_path,
            "target_dirs_path": target_dirs_path,
            "target_files_path": target_files_path,
            "slots": slots,
            "slot_order": slot_order,
            "on_max": on_max,
            "on_error": on_error,
        }

    def _validate_control_policy(self, node_id: str, value: Any, label: str) -> str:
        if value not in CONTROL_POLICIES:
            allowed = ", ".join(sorted(CONTROL_POLICIES))
            raise ValueError(f"Subgraph '{node_id}' {label} must be one of: {allowed}.")
        return str(value)

    def _validate_slot_order(self, node_id: str, value: Any) -> list[str]:
        if value is None:
            return list(SLOTS)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError(f"Subgraph '{node_id}' slot_order must be a list of slot names.")
        normalized = [item.lower() for item in value]
        if sorted(normalized) != sorted(SLOTS):
            expected = ", ".join(SLOTS)
            raise ValueError(f"Subgraph '{node_id}' slot_order must contain each AGENT_LOOP slot exactly once: {expected}.")
        return normalized

    def _create_slot_nodes(
        self,
        node_id: str,
        config: dict[str, Any],
    ) -> dict[str, capability_types.NodeCallable]:
        import lgwf.capabilities.registry as registry_module

        slot_nodes = {}
        slots = config["slots"]
        memory_ref = self._memory_context_ref(config["artifacts_path"])
        for slot_name, slot in slots.items():
            slot_node_id = f"{node_id}__{slot_name}"
            capability = slot["capability"]
            slot_config = dict(slot.get("config", {}))
            if capability == "exec.codex_prompt" and slot_name in MEMORY_CONTEXT_SLOTS:
                context_refs = list(slot_config.get("context_refs", []))
                if memory_ref not in context_refs:
                    context_refs.append(dict(memory_ref))
                slot_config["context_refs"] = context_refs
            slot_nodes[slot_name] = progress_module.wrap_node(
                slot_node_id,
                capability,
                registry_module.create_node(capability, slot_node_id, slot_config),
            )
        return slot_nodes

    def _run_loop(
        self,
        node_id: str,
        config: dict[str, Any],
        slot_nodes: dict[str, capability_types.NodeCallable],
        state: capability_types.State,
    ) -> capability_types.State:
        work_dir_root = runtime_context_module.get_work_dir_root() or runtime_context_module.get_workspace_root()
        if work_dir_root is None:
            work_dir_root = Path(".").resolve()
        workflow_root = runtime_context_module.get_workflow_root()
        loop_root = tool_operations_module.resolve_workspace_path(
            work_dir_root,
            config["artifacts_path"],
            "artifacts_path",
        )
        self._write_json(loop_root / "loop.json", self._loop_metadata(node_id, config))
        self._write_json(loop_root / "memory.json", self._initial_memory(node_id, config))

        current_state = dict(state)
        iteration_summaries: list[dict[str, Any]] = []
        failed_attempts: list[dict[str, Any]] = []
        final_status: dict[str, Any] | None = None
        final_report: dict[str, Any] | None = None
        token_usage = {
            "total_tokens": 0,
            "token_max": config["token_max"],
            "iteration_tokens": [],
        }

        for iteration in range(1, config["max_iterations"] + 1):
            status = {
                "loop_id": node_id,
                "status": "running",
                "current_iteration": iteration,
                "current_phase": config["slot_order"][0],
                "next": None,
                "stop_reason": None,
            }
            current_state = flow_conditions_module.write_path(current_state, config["status_path"], status)
            options = self._sandbox_options(config["artifacts_path"], iteration, workflow_root)
            prepare = tool_operations_module.sandbox_prepare(options, workspace_root=work_dir_root)
            candidate_root = Path(prepare["candidate_root"])
            candidate_work_dir = candidate_root / "work_dir"
            self._copy_memory_to_candidate(loop_root, candidate_work_dir, config["artifacts_path"])
            candidate_workflow_root = candidate_root / "target_dir" if workflow_root is not None else candidate_work_dir
            sandbox_client = client_factory_module.create_default_client(
                workflow_root=str(candidate_workflow_root),
                workspace_root=str(candidate_work_dir),
            )

            try:
                with runtime_context_module.use_work_dir_root(candidate_work_dir):
                    with runtime_context_module.use_workspace_root(candidate_work_dir):
                        with runtime_context_module.use_workflow_root(candidate_workflow_root):
                            with client_provider_module.use_client(sandbox_client):
                                iteration_start_state = current_state
                                iteration_state = self._run_iteration_slots(
                                    config,
                                    slot_nodes,
                                    current_state,
                                    iteration,
                                )

                verification = self._read_required_object(iteration_state, self._slot_result_path(config, "verify"), "verification")
                decision = self._read_required_object(iteration_state, self._slot_result_path(config, "decide"), "decision")
                passed = self._verification_passed(verification)
                category = self._decision_category(decision)
            except Exception as exc:
                iteration_state = current_state
                passed = False
                category = config["on_error"]
                verification = {
                    "passed": False,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
                decision = {
                    "category": category,
                    "reason": str(exc) or type(exc).__name__,
                    "evidence": [type(exc).__name__],
                    "stop_reason": "slot_error",
                }
                iteration_start_state = current_state
            promoted = False
            diff = tool_operations_module.sandbox_diff(options, workspace_root=work_dir_root)
            if passed and category in PROMOTE_CATEGORIES:
                tool_operations_module.sandbox_promote(options, workspace_root=work_dir_root)
                promoted = True

            loop_decision = {
                "category": category,
                "promoted": promoted,
                "reason": decision.get("reason"),
                "stop_reason": decision.get("stop_reason"),
                "diff": diff,
            }
            iteration_tokens = self._iteration_token_usage(node_id, iteration_start_state, iteration_state)
            token_usage["total_tokens"] += iteration_tokens
            token_usage["iteration_tokens"].append(
                {
                    "iteration": iteration,
                    "tokens": iteration_tokens,
                    "total_tokens": token_usage["total_tokens"],
                }
            )
            tool_operations_module.sandbox_archive(
                {
                    **options,
                    "validation": verification,
                    "decision": loop_decision,
                },
                workspace_root=work_dir_root,
            )
            self._archive_iteration(loop_root, iteration, config, iteration_state, verification, decision, loop_decision)

            iteration_summary = {
                "iteration": iteration,
                "passed": passed,
                "category": category,
                "promoted": promoted,
                "stop_reason": decision.get("stop_reason"),
                "token_usage": {
                    "tokens": iteration_tokens,
                    "total_tokens": token_usage["total_tokens"],
                },
            }
            iteration_summaries.append(iteration_summary)
            self._write_json(loop_root / "iterations.json", iteration_summaries)
            memory = self._memory(
                node_id,
                config,
                iteration,
                passed,
                verification,
                decision,
                loop_decision,
                iteration_summaries,
                failed_attempts,
            )
            failed_attempts = list(memory["failed_attempts"])
            self._write_json(loop_root / "memory.json", memory)

            current_state = iteration_state
            if category == "wait_human":
                stop_reason = decision.get("stop_reason") or "wait_human"
                final_status = self._status(node_id, "waiting_human", iteration, "human_decision", stop_reason, decision, token_usage)
                final_report = self._report(node_id, "waiting_human", iteration, stop_reason, iteration_summaries, decision, token_usage)
                break
            if category == "wait":
                stop_reason = decision.get("stop_reason") or "wait"
                final_status = self._status(node_id, "waiting", iteration, "wait", stop_reason, decision, token_usage)
                final_report = self._report(node_id, "waiting", iteration, stop_reason, iteration_summaries, decision, token_usage)
                break
            if passed and category == "finish":
                final_status = self._status(node_id, "finished", iteration, "finish", "target_succeeded", decision, token_usage)
                final_report = self._report(node_id, "finished", iteration, "target_succeeded", iteration_summaries, decision, token_usage)
                break
            if category == "block":
                stop_reason = decision.get("stop_reason") or ("validation_failed" if not passed else "unknown_blocker")
                final_status = self._status(node_id, "blocked", iteration, "block", stop_reason, decision, token_usage)
                final_report = self._report(node_id, "blocked", iteration, stop_reason, iteration_summaries, decision, token_usage)
                break
            if not passed and category not in {"continue", "retry"}:
                stop_reason = "validation_failed"
                final_status = self._status(node_id, "blocked", iteration, "block", stop_reason, decision, token_usage)
                final_report = self._report(node_id, "blocked", iteration, stop_reason, iteration_summaries, decision, token_usage)
                break
            if token_usage["total_tokens"] >= config["token_max"]:
                stop_reason = "token_max_reached"
                final_status = self._status(node_id, "waiting_human", iteration, "human_decision", stop_reason, decision, token_usage)
                final_report = self._report(node_id, "waiting_human", iteration, stop_reason, iteration_summaries, decision, token_usage)
                break
            if iteration == config["max_iterations"]:
                stop_reason = "max_attempts_reached"
                if config["on_max"] == "wait_human":
                    final_status = self._status(node_id, "waiting_human", iteration, "human_decision", stop_reason, decision, token_usage)
                    final_report = self._report(node_id, "waiting_human", iteration, stop_reason, iteration_summaries, decision, token_usage)
                else:
                    final_status = self._status(node_id, "blocked", iteration, "block", stop_reason, decision, token_usage)
                    final_report = self._report(node_id, "blocked", iteration, stop_reason, iteration_summaries, decision, token_usage)
                break

        if final_status is None or final_report is None:
            raise RuntimeError(f"Subgraph '{node_id}' exited without a final status.")

        current_state = flow_conditions_module.write_path(current_state, config["status_path"], final_status)
        current_state = flow_conditions_module.write_path(current_state, config["report_path"], final_report)
        self._write_json(loop_root / "report.json", final_report)
        return current_state

    def _run_iteration_slots(
        self,
        config: dict[str, Any],
        slot_nodes: dict[str, capability_types.NodeCallable],
        state: capability_types.State,
        iteration: int,
    ) -> capability_types.State:
        current_state = dict(state)
        for slot_name in config["slot_order"]:
            status = dict(flow_conditions_module.read_path(current_state, config["status_path"]))
            status["current_phase"] = slot_name
            status["current_iteration"] = iteration
            current_state = flow_conditions_module.write_path(current_state, config["status_path"], status)
            current_state = slot_nodes[slot_name](current_state)
        return current_state

    def _sandbox_options(
        self,
        artifacts_path: str,
        iteration: int,
        workflow_root: Path | None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "sandbox_path": f"{artifacts_path}/iterations/{iteration:03d}/sandbox",
            "work_dir": {
                "include": ["**"],
                "promote_include": ["**"],
            },
        }
        if workflow_root is not None:
            options["target_dir"] = {
                "_source_root": workflow_root,
                "include": ["**"],
                "promote_include": ["**"],
            }
        return options

    def _archive_iteration(
        self,
        loop_root: Path,
        iteration: int,
        config: dict[str, Any],
        state: dict[str, Any],
        verification: dict[str, Any],
        decision: dict[str, Any],
        loop_decision: dict[str, Any],
    ) -> None:
        current_root = loop_root / "current"
        iteration_root = loop_root / "iterations" / f"{iteration:03d}"
        for root in (current_root, iteration_root):
            self._write_json(root / "verification.json", verification)
            self._write_json(root / "decision.json", decision)
            self._write_json(root / "loop_decision.json", loop_decision)
            for slot_name, artifact_name in (
                ("observe", "observation"),
                ("diagnose", "diagnosis"),
                ("plan", "plan"),
                ("act", "action"),
            ):
                value = flow_conditions_module.read_path(state, self._slot_result_path(config, slot_name))
                if value is not None:
                    self._write_json(root / f"{artifact_name}.json", value)

    def _memory_context_ref(self, artifacts_path: str) -> dict[str, str]:
        return {
            "root": "workspace",
            "type": "file",
            "path": f"{artifacts_path}/memory.json",
        }

    def _copy_memory_to_candidate(self, loop_root: Path, candidate_work_dir: Path, artifacts_path: str) -> None:
        memory_path = loop_root / "memory.json"
        if not memory_path.is_file():
            return
        candidate_memory_path = candidate_work_dir / artifacts_path / "memory.json"
        candidate_memory_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_memory_path.write_text(memory_path.read_text(encoding="utf-8"), encoding="utf-8")

    def _initial_memory(self, node_id: str, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "loop_id": node_id,
            "goal": config["goal"],
            "current_status": "pending",
            "last_iteration": 0,
            "completed": [],
            "open_issues": [],
            "failed_attempts": [],
            "constraints": [],
            "next_recommendation": "Start the first iteration.",
            "last_verification": None,
            "last_decision": None,
            "last_diff_summary": {"total": 0, "by_status": {}, "sample": []},
            "iteration_summaries": [],
        }

    def _memory(
        self,
        node_id: str,
        config: dict[str, Any],
        iteration: int,
        passed: bool,
        verification: dict[str, Any],
        decision: dict[str, Any],
        loop_decision: dict[str, Any],
        iteration_summaries: list[dict[str, Any]],
        failed_attempts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        next_failed_attempts = list(failed_attempts)
        if not passed:
            next_failed_attempts.append(
                {
                    "iteration": iteration,
                    "reason": decision.get("reason") or verification.get("message") or "verification failed",
                    "evidence": self._bounded_string_list(decision.get("evidence", []), 5),
                    "stop_reason": decision.get("stop_reason"),
                }
            )
        next_failed_attempts = next_failed_attempts[-MEMORY_FAILED_ATTEMPTS_LIMIT:]

        completed = []
        if passed:
            reason = decision.get("reason")
            if isinstance(reason, str) and reason:
                completed.append(reason)

        open_issues = []
        if not passed:
            issue = verification.get("message") or decision.get("reason") or decision.get("stop_reason")
            if isinstance(issue, str) and issue:
                open_issues.append(issue)

        return {
            "loop_id": node_id,
            "goal": config["goal"],
            "current_status": self._memory_status(passed, str(decision.get("category", ""))),
            "last_iteration": iteration,
            "completed": completed,
            "open_issues": open_issues,
            "failed_attempts": next_failed_attempts,
            "constraints": [],
            "next_recommendation": self._next_recommendation(passed, decision),
            "last_verification": dict(verification),
            "last_decision": dict(decision),
            "last_diff_summary": self._diff_summary(loop_decision.get("diff")),
            "iteration_summaries": [dict(item) for item in iteration_summaries],
        }

    def _memory_status(self, passed: bool, category: str) -> str:
        if passed and category == "finish":
            return "finished"
        if category == "wait_human":
            return "waiting_human"
        if category == "wait":
            return "waiting"
        if category == "block":
            return "blocked"
        if category == "retry" or not passed:
            return "retrying"
        return "continuing"

    def _next_recommendation(self, passed: bool, decision: dict[str, Any]) -> str:
        reason = decision.get("reason")
        if isinstance(reason, str) and reason:
            return reason
        if passed:
            return "Continue from the accepted iteration result."
        return "Address the open issues before the next iteration."

    def _diff_summary(self, diff: Any) -> dict[str, Any]:
        if not isinstance(diff, dict):
            return {"total": 0, "by_status": {}, "sample": []}
        changes = diff.get("changes", [])
        if not isinstance(changes, list):
            changes = []
        by_status: dict[str, int] = {}
        sample = []
        for item in changes:
            if not isinstance(item, dict):
                continue
            status = item.get("status")
            if isinstance(status, str) and status:
                by_status[status] = by_status.get(status, 0) + 1
            if len(sample) < MEMORY_CHANGE_PATH_LIMIT:
                sample.append(
                    {
                        "root": item.get("root"),
                        "path": item.get("path"),
                        "status": item.get("status"),
                    }
                )
        return {
            "total": len(changes),
            "by_status": by_status,
            "sample": sample,
        }

    def _bounded_string_list(self, value: Any, limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        result = []
        for item in value:
            if isinstance(item, str):
                result.append(item)
            if len(result) >= limit:
                break
        return result

    def _loop_metadata(self, node_id: str, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "loop_id": node_id,
            "goal": config["goal"],
            "max_iterations": config["max_iterations"],
            "token_max": config["token_max"],
            "artifacts_path": config["artifacts_path"],
            "target_dirs_path": config["target_dirs_path"],
            "target_files_path": config["target_files_path"],
            "slot_order": config["slot_order"],
            "on_max": config["on_max"],
            "on_error": config["on_error"],
        }

    def _status(
        self,
        node_id: str,
        status: str,
        iteration: int,
        next_value: str,
        stop_reason: str,
        decision: dict[str, Any],
        token_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        status_data = {
            "loop_id": node_id,
            "status": status,
            "current_iteration": iteration,
            "current_phase": "decide",
            "next": next_value,
            "stop_reason": stop_reason,
            "reason": decision.get("reason"),
            "evidence": decision.get("evidence", []),
        }
        if token_usage is not None:
            status_data["token_usage"] = token_usage
        return status_data

    def _report(
        self,
        node_id: str,
        status: str,
        iteration: int,
        stop_reason: str,
        iterations: list[dict[str, Any]],
        decision: dict[str, Any],
        token_usage: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        report = {
            "loop_id": node_id,
            "status": status,
            "iterations": iteration,
            "stop_reason": stop_reason,
            "reason": decision.get("reason"),
            "evidence": decision.get("evidence", []),
            "iteration_summaries": iterations,
        }
        if token_usage is not None:
            report["token_usage"] = token_usage
        return report

    def _iteration_token_usage(self, node_id: str, before_state: dict[str, Any], after_state: dict[str, Any]) -> int:
        before_total = self._run_token_total(before_state)
        after_total = self._run_token_total(after_state)
        run_delta = max(after_total - before_total, 0)
        if run_delta:
            return run_delta

        total = 0
        for slot_name in SLOTS:
            value = flow_conditions_module.read_path(after_state, f"token_usage.{node_id}__{slot_name}")
            total += self._token_usage_total(value)
        return total

    def _run_token_total(self, state: dict[str, Any]) -> int:
        return self._token_usage_total(flow_conditions_module.read_path(state, "run.token_usage.totals"))

    def _token_usage_total(self, value: Any) -> int:
        if isinstance(value, dict):
            token_value = value.get("total_tokens")
            if isinstance(token_value, int | float) and token_value >= 0:
                return int(token_value)
        return 0

    def _slot_result_path(self, config: dict[str, Any], slot_name: str) -> str:
        slot_config = config["slots"][slot_name].get("config", {})
        result_path = slot_config.get("result_path")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError(f"subgraph.agent_loop {slot_name} slot requires config.result_path.")
        return result_path

    def _read_required_object(self, state: dict[str, Any], path: str, label: str) -> dict[str, Any]:
        value = flow_conditions_module.read_path(state, path)
        if not isinstance(value, dict):
            raise ValueError(f"subgraph.agent_loop {label} result must be an object at state path: {path}")
        return value

    def _verification_passed(self, verification: dict[str, Any]) -> bool:
        passed = verification.get("passed")
        if not isinstance(passed, bool):
            raise ValueError("subgraph.agent_loop verification result requires boolean passed.")
        return passed

    def _decision_category(self, decision: dict[str, Any]) -> str:
        category = decision.get("category")
        if category not in {"continue", "retry", "wait", "wait_human", "finish", "block"}:
            raise ValueError("subgraph.agent_loop decision result requires a valid category.")
        reason = decision.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ValueError("subgraph.agent_loop decision result requires reason.")
        return category

    def _validate_relative_path(self, node_id: str, raw_path: str, label: str) -> None:
        path = Path(raw_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Subgraph '{node_id}' {label} must be relative and must not contain '..'.")

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


CAPABILITY = SubgraphAgentLoopCapability()
