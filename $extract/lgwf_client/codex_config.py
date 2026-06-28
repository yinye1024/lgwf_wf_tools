import pathlib
from typing import Any

import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module


DEFAULT_CODEX_MODEL = "gpt-5.4"
CONFIG_VERSION = 1


def get_codex_model(workspace_root: str | pathlib.Path) -> dict[str, Any]:
    config_path = workspace_layout_module.codex_config_path(workspace_root)
    payload: dict[str, Any] = {
        "model": DEFAULT_CODEX_MODEL,
        "source": "default",
        "default_model": DEFAULT_CODEX_MODEL,
        "config_path": str(config_path),
    }
    if not config_path.is_file():
        return payload

    config = file_ops_module.read_json_object(config_path, label="Codex config")
    model = _normalize_model(config.get("model"))
    payload["model"] = model
    payload["source"] = "workspace"
    return payload


def set_codex_model(workspace_root: str | pathlib.Path, model: str) -> dict[str, Any]:
    normalized_model = _normalize_model(model)
    config_path = workspace_layout_module.codex_config_path(workspace_root)
    file_ops_module.write_json_atomic(
        config_path,
        {
            "version": CONFIG_VERSION,
            "model": normalized_model,
        },
    )
    payload = get_codex_model(workspace_root)
    payload["ok"] = True
    return payload


def reset_codex_model(workspace_root: str | pathlib.Path) -> dict[str, Any]:
    config_path = workspace_layout_module.codex_config_path(workspace_root)
    config_path.unlink(missing_ok=True)
    payload = get_codex_model(workspace_root)
    payload["ok"] = True
    return payload


def _normalize_model(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("model must be a non-empty string.")
    model = value.strip()
    if any(char.isspace() for char in model):
        raise ValueError("model must not contain whitespace.")
    return model
