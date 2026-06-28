from pathlib import Path
from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types
import lgwf.client_provider as client_provider_module
import lgwf.runtime_context as runtime_context_module
import lgwf_client.client_factory as client_factory_module
import lgwf_client.tools.operations as tool_operations_module


class ValidationSandboxCapability:
    name = "subgraph.validation_sandbox"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        sandbox_options = _sandbox_options(node_id, config)
        workflow = config.get("workflow")
        if not isinstance(workflow, dict):
            raise ValueError(f"Subgraph '{node_id}' requires a workflow object.")
        result_path = config.get("result_path", "sandbox")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError(f"Subgraph '{node_id}' result_path must be a non-empty string when provided.")

        import lgwf.compiler.dsl as compiler_module

        compiler_module.validate_dsl(workflow)
        graph = compiler_module.compile_dsl(workflow)

        def node(state: capability_types.State) -> capability_types.State:
            work_dir_root = runtime_context_module.get_workspace_root() or Path(".").resolve()
            workflow_root = runtime_context_module.get_workflow_root()
            active_options = dict(sandbox_options)
            if "target_dir" in sandbox_options and workflow_root is not None:
                active_options["target_dir"] = {
                    **sandbox_options["target_dir"],
                    "_source_root": workflow_root,
                }
            prepare = tool_operations_module.sandbox_prepare(active_options, workspace_root=work_dir_root)
            candidate_root = Path(prepare["candidate_root"])
            candidate_work_dir = candidate_root / "work_dir"
            candidate_workflow_root = candidate_work_dir
            if "target_dir" in active_options:
                candidate_workflow_root = candidate_root / "target_dir"

            sandbox_client = client_factory_module.create_default_client(
                workflow_root=str(candidate_workflow_root),
                workspace_root=str(candidate_work_dir),
            )
            try:
                with runtime_context_module.use_workspace_root(candidate_work_dir):
                    with runtime_context_module.use_workflow_root(candidate_workflow_root):
                        with client_provider_module.use_client(sandbox_client):
                            final_state = graph.invoke(state)
                diff = tool_operations_module.sandbox_diff(active_options, workspace_root=work_dir_root)
                promote = tool_operations_module.sandbox_promote(active_options, workspace_root=work_dir_root)
                decision = {
                    "status": "promoted",
                    "diff": diff,
                    "promote": promote,
                }
                archive = tool_operations_module.sandbox_archive(
                    {
                        **active_options,
                        "validation": {"status": "passed"},
                        "decision": decision,
                    },
                    workspace_root=work_dir_root,
                )
                return flow_conditions_module.write_path(
                    final_state,
                    result_path,
                    {
                        **decision,
                        "sandbox_root": archive["sandbox_root"],
                    },
                )
            except Exception as exc:
                failure = {"type": type(exc).__name__, "message": str(exc)}
                try:
                    diff = tool_operations_module.sandbox_diff(active_options, workspace_root=work_dir_root)
                except Exception as diff_exc:
                    diff = {"error": type(diff_exc).__name__, "message": str(diff_exc)}
                tool_operations_module.sandbox_archive(
                    {
                        **active_options,
                        "validation": {"status": "failed", "failure": failure},
                        "decision": {"status": "failed", "diff": diff, "failure": failure},
                    },
                    workspace_root=work_dir_root,
                )
                raise

        return node


def _sandbox_options(node_id: str, config: dict[str, Any]) -> dict[str, Any]:
    sandbox_path = config.get("sandbox_path")
    if not isinstance(sandbox_path, str) or not sandbox_path:
        raise ValueError(f"Subgraph '{node_id}' requires sandbox_path.")
    work_dir = _root_options(node_id, config.get("work_dir"), "work_dir")
    options: dict[str, Any] = {
        "sandbox_path": sandbox_path,
        "work_dir": work_dir,
    }
    target_dir = config.get("target_dir")
    if target_dir is not None:
        if not isinstance(target_dir, dict):
            raise ValueError(f"Subgraph '{node_id}' target_dir must be an object when provided.")
        root = target_dir.get("root", "workspace")
        if root != "workspace":
            raise ValueError(f"Subgraph '{node_id}' target_dir.root must be workspace.")
        path = target_dir.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(f"Subgraph '{node_id}' target_dir.path must be a non-empty string.")
        options["target_dir"] = {
            **_root_options(node_id, target_dir, "target_dir"),
            "path": path,
        }
    return options


def _root_options(node_id: str, raw_root: object, label: str) -> dict[str, Any]:
    if not isinstance(raw_root, dict):
        raise ValueError(f"Subgraph '{node_id}' {label} must be an object.")
    include = _string_list(node_id, raw_root.get("include"), f"{label}.include")
    promote_include = _string_list(node_id, raw_root.get("promote_include"), f"{label}.promote_include")
    exclude = _string_list(node_id, raw_root.get("exclude", []), f"{label}.exclude", allow_empty=True)
    return {
        "include": include,
        "exclude": exclude,
        "promote_include": promote_include,
    }


def _string_list(node_id: str, value: object, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"Subgraph '{node_id}' {label} must be a non-empty list.")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"Subgraph '{node_id}' {label} must contain strings.")
    return list(value)


CAPABILITY = ValidationSandboxCapability()
