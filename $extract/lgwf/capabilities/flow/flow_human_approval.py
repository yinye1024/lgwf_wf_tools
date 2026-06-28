from pathlib import Path
from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types
import lgwf.human_approval as human_approval_module
import lgwf.progress as progress_module
import lgwf.runtime_context as runtime_context_module
import lgwf_tools.file_ops as file_ops_module


class FlowHumanApprovalCapability:
    name = "flow.human_approval"

    def create_node(self, _node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        prompt = config.get("prompt")
        prompt_ref = config.get("prompt_ref")
        context_path = config.get("context_path")
        approved_value_path = config.get("approved_value_path")
        result_path = config.get("result_path", "human_approval")
        persist_value_path = config.get("persist_value_path")
        timeout_seconds = config.get("timeout_seconds")
        poll_interval_seconds = config.get("poll_interval_seconds", 1)

        if (prompt is None) == (prompt_ref is None):
            raise ValueError("flow.human_approval config requires exactly one of prompt or prompt_ref.")
        if prompt is not None and (not isinstance(prompt, str) or not prompt.strip()):
            raise ValueError("flow.human_approval config.prompt must be a non-empty string.")
        if not isinstance(context_path, str) or not context_path:
            raise ValueError("flow.human_approval config.context_path must be a non-empty string.")
        if not isinstance(approved_value_path, str) or not approved_value_path:
            raise ValueError("flow.human_approval config.approved_value_path must be a non-empty string.")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError("flow.human_approval config.result_path must be a non-empty string.")
        if persist_value_path is not None and (
            not isinstance(persist_value_path, str) or not persist_value_path
        ):
            raise ValueError("flow.human_approval config.persist_value_path must be a non-empty string when provided.")
        if timeout_seconds is not None and (
            not isinstance(timeout_seconds, int | float) or timeout_seconds <= 0
        ):
            raise ValueError("flow.human_approval config.timeout_seconds must be a positive number or null.")
        if not isinstance(poll_interval_seconds, int | float) or poll_interval_seconds <= 0:
            raise ValueError("flow.human_approval config.poll_interval_seconds must be a positive number.")

        def node(state: capability_types.State) -> capability_types.State:
            workspace_root = runtime_context_module.get_workspace_root()
            if workspace_root is None:
                raise RuntimeError("flow.human_approval requires a runtime workspace root.")
            resolved_prompt = prompt if prompt is not None else _read_workflow_prompt(prompt_ref)
            context = flow_conditions_module.read_path(state, context_path)
            request = human_approval_module.create_request(
                workspace_root=workspace_root,
                prompt=resolved_prompt,
                context=context,
            )
            progress_module.emit(
                f"[workflow] human approval pending request_id={request['request_id']}"
            )
            response = human_approval_module.wait_for_response(
                workspace_root=workspace_root,
                request_id=request["request_id"],
                timeout_seconds=None if timeout_seconds is None else float(timeout_seconds),
                poll_interval_seconds=float(poll_interval_seconds),
            )
            if response["decision"] == "reject":
                raise RuntimeError(f"Human approval rejected: {response.get('comment', '')}")

            next_state = dict(state)
            next_state = flow_conditions_module.write_path(next_state, approved_value_path, response["value"])
            if persist_value_path is not None:
                target = file_ops_module.resolve_under_root(workspace_root, persist_value_path)
                file_ops_module.write_json_atomic(target, response["value"])
            result = {
                "request_id": request["request_id"],
                "decision": response["decision"],
                "comment": response.get("comment", ""),
            }
            return flow_conditions_module.write_path(next_state, result_path, result)

        return node


CAPABILITY = FlowHumanApprovalCapability()


def _read_workflow_prompt(prompt_ref: Any) -> str:
    if not isinstance(prompt_ref, dict):
        raise ValueError("flow.human_approval config.prompt_ref must be an object.")
    if prompt_ref.get("root") != "workflow":
        raise ValueError("flow.human_approval config.prompt_ref.root must be workflow.")
    raw_path = prompt_ref.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("flow.human_approval config.prompt_ref.path must be a non-empty string.")
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("flow.human_approval config.prompt_ref.path must be relative and must not contain '..'.")
    workflow_root = runtime_context_module.get_workflow_root()
    if workflow_root is None:
        raise RuntimeError("flow.human_approval prompt_ref requires a runtime workflow root.")
    resolved = (workflow_root / path).resolve()
    if not resolved.is_relative_to(workflow_root):
        raise ValueError("flow.human_approval config.prompt_ref.path must stay inside the workflow root.")
    if not resolved.is_file():
        raise ValueError(f"flow.human_approval prompt_ref does not exist or is not a file: {resolved}")
    return resolved.read_text(encoding="utf-8")
