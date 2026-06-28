import pathlib
from collections.abc import Callable
from typing import Any

import lgwf_client.tools.catalog as catalog_module
import lgwf_client.tools.operations as operations_module


ToolOperation = Callable[..., dict[str, Any]]


_OPERATIONS: dict[str, ToolOperation] = {
    "copy_directory": operations_module.copy_directory,
    "copy_file": operations_module.copy_file,
    "ensure_dir": operations_module.ensure_dir,
    "file_replace": operations_module.file_replace,
    "sandbox_archive": operations_module.sandbox_archive,
    "sandbox_diff": operations_module.sandbox_diff,
    "sandbox_prepare": operations_module.sandbox_prepare,
    "sandbox_promote": operations_module.sandbox_promote,
    "write_text_file": operations_module.write_text_file,
}


TOOLS: dict[str, dict[str, Any]] = {
    name: {**descriptor, "operation": _OPERATIONS[name]}
    for name, descriptor in catalog_module.tool_descriptors().items()
}


def list_public_tools() -> list[dict[str, Any]]:
    return [_public_descriptor(TOOLS[name]) for name in sorted(TOOLS) if TOOLS[name]["public"]]


def describe_public_tool(name: object) -> dict[str, Any]:
    descriptor = _resolve_public_tool(name)
    return _public_descriptor(descriptor)


def run_cli_tool(
    name: object,
    options: dict[str, Any],
    *,
    work_dir: pathlib.Path | None = None,
    cwd: pathlib.Path | None = None,
) -> dict[str, Any]:
    descriptor = _resolve_public_tool(name)
    catalog_module.validate_public_tool_options(name, options)
    operation: ToolOperation = descriptor["operation"]
    if descriptor["path_mode"] == "workspace":
        if work_dir is None:
            raise ValueError(f"--work-dir is required for tool: {descriptor['name']}")
        return operation(options, workspace_root=work_dir.resolve())
    return operation(options, cwd=cwd)


def run_builtin_tool(
    name: object,
    options: dict[str, Any],
    workspace_root: pathlib.Path,
) -> dict[str, Any]:
    descriptor = _resolve_public_tool(name)
    catalog_module.validate_public_tool_options(name, options)
    operation: ToolOperation = descriptor["operation"]
    return operation(options, workspace_root=workspace_root.resolve())


def _resolve_public_tool(name: object) -> dict[str, Any]:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("tool name must be a non-empty string.")
    descriptor = TOOLS.get(name)
    if descriptor is None or not descriptor["public"]:
        raise ValueError(f"Unknown public tool: {name}")
    return descriptor


def _public_descriptor(descriptor: dict[str, Any]) -> dict[str, Any]:
    return {
        key: descriptor[key]
        for key in (
            "name",
            "description",
            "path_mode",
            "mutates_files",
            "options_schema",
        )
    }
