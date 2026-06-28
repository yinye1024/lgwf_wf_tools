from collections import Counter
from pathlib import Path
from typing import Any

import lgwf.capabilities.exec.exec_state as exec_state_module
import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types
import lgwf_client.context_manifest as context_manifest_module
import lgwf_client.types as client_types


class ExecInspectProjectCapability:
    name = "exec.inspect_project"

    def create_node(self, _node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        cwd = config.get("cwd", ".")
        max_files = config.get("max_files", 500)
        refresh = config.get("refresh", True)
        context_path = config.get("context_path", "project_context")

        if not isinstance(cwd, str) or not cwd.strip():
            raise ValueError("exec.inspect_project config.cwd must be a non-empty string.")
        if not isinstance(max_files, int) or max_files <= 0:
            raise ValueError("exec.inspect_project config.max_files must be a positive integer.")
        if not isinstance(refresh, bool):
            raise ValueError("exec.inspect_project config.refresh must be a boolean.")
        if not isinstance(context_path, str) or not context_path:
            raise ValueError("exec.inspect_project config.context_path must be a non-empty string.")

        def node(state: capability_types.State) -> capability_types.State:
            workspace_root = Path(cwd)
            if refresh:
                manifest = context_manifest_module.refresh_manifest(workspace_root, max_files=max_files)
            else:
                manifest = context_manifest_module.load_manifest(workspace_root)

            summary = self._summary(manifest)
            next_state = exec_state_module.public_state(state)
            next_state = flow_conditions_module.write_path(next_state, context_path, summary)
            return next_state

        return node

    def _summary(self, manifest: client_types.WorkspaceContext) -> dict[str, Any]:
        files = manifest["files"]
        extensions = Counter(_extension(item["path"]) for item in files)
        top_dirs = Counter(_top_dir(item["path"]) for item in files)

        return {
            "workspace_root": manifest["workspace_root"],
            "manifest_path": context_manifest_module.manifest_path(Path(manifest["workspace_root"])).as_posix(),
            "generated_at": manifest["generated_at"],
            "stats": manifest["stats"],
            "top_extensions": dict(extensions.most_common(10)),
            "top_dirs": dict(top_dirs.most_common(10)),
            "sample_files": [item["path"] for item in files[:20]],
        }


def _extension(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix:
        return suffix
    return "<none>"


def _top_dir(path: str) -> str:
    parts = Path(path).parts
    if len(parts) > 1:
        return parts[0]
    return "<root>"


CAPABILITY = ExecInspectProjectCapability()

