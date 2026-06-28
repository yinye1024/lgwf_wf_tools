import json
import pathlib
from collections.abc import Callable
from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.route_keys as route_key_module
import lgwf.capabilities.types as capability_types
import lgwf.runtime_context as runtime_context_module


CheckResult = dict[str, Any]
CheckFunction = Callable[[dict[str, Any], pathlib.Path], CheckResult]


class FlowCheckCapability:
    name = "flow.check"

    def __init__(self, workspace_root: str | pathlib.Path | None = None) -> None:
        self._workspace_root = pathlib.Path(workspace_root).resolve() if workspace_root is not None else None

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        check = config.get("check")
        options = config.get("options", {})
        result_path = config.get("result_path", "last_check")
        pass_route = config.get("pass_route", "pass")
        fail_route = config.get("fail_route", "fail")

        if not isinstance(check, str) or not check.strip():
            raise ValueError("flow.check config.check must be a non-empty string.")
        if not isinstance(options, dict):
            raise ValueError("flow.check config.options must be an object.")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError("flow.check config.result_path must be a non-empty string.")
        if not isinstance(pass_route, str) or not pass_route:
            raise ValueError("flow.check config.pass_route must be a non-empty string.")
        if not isinstance(fail_route, str) or not fail_route:
            raise ValueError("flow.check config.fail_route must be a non-empty string.")

        try:
            check_function = CHECKS[check]
        except KeyError as exc:
            raise ValueError(f"Unknown flow.check check: {check}") from exc

        def node(state: capability_types.State) -> capability_types.State:
            workspace_root = self._workspace_root or runtime_context_module.get_workspace_root() or pathlib.Path.cwd().resolve()
            result = check_function(options, workspace_root)
            route = pass_route if result["ok"] else fail_route
            next_state = flow_conditions_module.write_path(state, result_path, result)
            next_state[route_key_module.route_key_for(node_id)] = route
            return next_state

        return node


def artifact_exists(options: dict[str, Any], workspace_root: pathlib.Path) -> CheckResult:
    return _path_result("artifact_exists", options, workspace_root, lambda path: path.exists(), "exists")


def dir_exists(options: dict[str, Any], workspace_root: pathlib.Path) -> CheckResult:
    return _path_result("dir_exists", options, workspace_root, lambda path: path.is_dir(), "is directory")


def file_exists(options: dict[str, Any], workspace_root: pathlib.Path) -> CheckResult:
    return _path_result("file_exists", options, workspace_root, lambda path: path.is_file(), "is file")


def file_not_exists(options: dict[str, Any], workspace_root: pathlib.Path) -> CheckResult:
    return _path_result("file_not_exists", options, workspace_root, lambda path: not path.exists(), "does not exist")


def json_field_exists(options: dict[str, Any], workspace_root: pathlib.Path) -> CheckResult:
    data, path, field, exists, value = _read_json_field(options, workspace_root)
    return _result(
        "json_field_exists",
        exists,
        f"JSON field {field} exists." if exists else f"JSON field {field} does not exist.",
        {"path": str(path), "field": field, "value": value if exists else None, "json_type": type(data).__name__},
    )


def json_field_equals(options: dict[str, Any], workspace_root: pathlib.Path) -> CheckResult:
    _data, path, field, exists, value = _read_json_field(options, workspace_root)
    expected = options.get("value")
    ok = exists and value == expected
    return _result(
        "json_field_equals",
        ok,
        f"JSON field {field} equals expected value." if ok else f"JSON field {field} does not equal expected value.",
        {"path": str(path), "field": field, "value": value if exists else None, "expected": expected, "exists": exists},
    )


def json_field_in(options: dict[str, Any], workspace_root: pathlib.Path) -> CheckResult:
    values = options.get("values")
    if not isinstance(values, list):
        raise ValueError("flow.check json_field_in options.values must be a list.")
    _data, path, field, exists, value = _read_json_field(options, workspace_root)
    ok = exists and value in values
    return _result(
        "json_field_in",
        ok,
        f"JSON field {field} is in allowed values." if ok else f"JSON field {field} is not in allowed values.",
        {"path": str(path), "field": field, "value": value if exists else None, "values": values, "exists": exists},
    )


CHECKS: dict[str, CheckFunction] = {
    "artifact_exists": artifact_exists,
    "dir_exists": dir_exists,
    "file_exists": file_exists,
    "file_not_exists": file_not_exists,
    "json_field_equals": json_field_equals,
    "json_field_exists": json_field_exists,
    "json_field_in": json_field_in,
}


def _path_result(
    name: str,
    options: dict[str, Any],
    workspace_root: pathlib.Path,
    predicate: Callable[[pathlib.Path], bool],
    expectation: str,
) -> CheckResult:
    path = _resolve_workspace_path(options.get("path"), workspace_root, "options.path")
    ok = predicate(path)
    return _result(
        name,
        ok,
        f"Path {path} {expectation}." if ok else f"Path {path} failed check: {expectation}.",
        {"path": str(path)},
    )


def _read_json_field(options: dict[str, Any], workspace_root: pathlib.Path) -> tuple[Any, pathlib.Path, str, bool, Any]:
    path = _resolve_workspace_path(options.get("path"), workspace_root, "options.path")
    field = options.get("field")
    if not isinstance(field, str) or not field:
        raise ValueError("flow.check JSON checks require options.field to be a non-empty string.")
    if not path.is_file():
        raise ValueError(f"flow.check JSON path does not exist or is not a file: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file for flow.check: {path}") from exc

    exists, value = _read_field(data, field)
    return data, path, field, exists, value


def _read_field(data: Any, field: str) -> tuple[bool, Any]:
    current = data
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _resolve_workspace_path(raw_path: Any, workspace_root: pathlib.Path, label: str) -> pathlib.Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"flow.check {label} must be a non-empty string.")
    path = pathlib.Path(raw_path)
    if path.is_absolute():
        raise ValueError(f"flow.check {label} must be relative.")
    if ".." in path.parts:
        raise ValueError(f"flow.check {label} must not contain '..'.")
    root = workspace_root.resolve()
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"flow.check {label} must stay inside workspace root.")
    return resolved


def _result(name: str, ok: bool, message: str, details: dict[str, Any]) -> CheckResult:
    return {
        "name": name,
        "ok": ok,
        "message": message,
        "details": details,
    }


CAPABILITY = FlowCheckCapability()
