from __future__ import annotations

import json
from pathlib import Path
from typing import Any


STATE_ROOT = "lgwf_wf_prompt_fix"
PROMPT_FIX_TARGET = "prompt_fix_target.json"


def workspace_root() -> Path:
    return Path.cwd()


def lgwf_dir(root: Path | None = None) -> Path:
    base = root or workspace_root()
    path = base / ".lgwf"
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def output_state(updates: dict[str, Any], *, next_key: str | None = None, route_node: str | None = None) -> None:
    payload: dict[str, Any] = {f"{STATE_ROOT}.{key}": value for key, value in updates.items()}
    if next_key is not None:
        if not route_node:
            raise ValueError("route_node is required when next_key is set")
        payload[f"__route__{route_node}"] = next_key
    print(json.dumps(payload, ensure_ascii=False))


def load_prompt_fix_target() -> dict[str, Any]:
    data = read_json(lgwf_dir() / PROMPT_FIX_TARGET, {})
    if not isinstance(data, dict):
        raise ValueError(f".lgwf/{PROMPT_FIX_TARGET} must contain a JSON object")
    return data


def write_prompt_fix_target(target: dict[str, Any]) -> None:
    write_json(lgwf_dir() / PROMPT_FIX_TARGET, target)
