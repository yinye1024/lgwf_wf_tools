import lgwf_client.client as client_module
import lgwf_client.runners.codex_runner as codex_runner_module
import lgwf_client.runners.python_runner as python_runner_module
import lgwf_client.runners.shell_runner as shell_runner_module
import lgwf_client.runners.tool_runner as tool_runner_module


def create_default_client(
    workflow_root: str | None = None,
    workspace_root: str | None = None,
) -> client_module.LocalClient:
    return client_module.LocalClient(
        runners=[
            shell_runner_module.ShellRunner(
                workflow_root=workflow_root,
                workspace_root=workspace_root,
            ),
            python_runner_module.PythonRunner(
                workflow_root=workflow_root,
                workspace_root=workspace_root,
            ),
            tool_runner_module.ToolRunner(workspace_root=workspace_root),
            codex_runner_module.CodexRunner(
                workflow_root=workflow_root,
                workspace_root=workspace_root,
            ),
        ]
    )

