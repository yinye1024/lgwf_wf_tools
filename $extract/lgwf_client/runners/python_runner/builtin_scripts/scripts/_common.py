import argparse
import json
import os
import pathlib
from typing import Any


def load_options() -> dict[str, Any]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--options-json", default="{}")
    namespace, _remaining = parser.parse_known_args()
    try:
        options = json.loads(namespace.options_json)
    except json.JSONDecodeError as exc:
        raise ValueError("--options-json must be a JSON object.") from exc
    if not isinstance(options, dict):
        raise ValueError("--options-json must be a JSON object.")
    return options


def resolve_workspace_path(raw_path: object, label: str) -> pathlib.Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"{label} must be a non-empty string.")
    path = pathlib.Path(raw_path)
    if path.is_absolute():
        raise ValueError(f"{label} must be relative.")
    if ".." in path.parts:
        raise ValueError(f"{label} must not contain '..'.")

    root = workspace_root()
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"{label} must stay inside workspace root.")
    return resolved


def workspace_root() -> pathlib.Path:
    raw_root = os.environ.get("LGWF_WORKSPACE_ROOT")
    if not raw_root:
        raise ValueError("LGWF_WORKSPACE_ROOT must be set for builtin scripts.")
    root = pathlib.Path(raw_root).resolve()
    if not root.is_dir():
        raise ValueError("LGWF_WORKSPACE_ROOT must point to an existing directory.")
    return root


def looks_binary(data: bytes) -> bool:
    return b"\x00" in data
