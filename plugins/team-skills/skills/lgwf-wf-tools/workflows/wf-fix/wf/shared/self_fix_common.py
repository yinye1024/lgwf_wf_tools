from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


STATE_ROOT = "lgwf_wf_fix"


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


def read_text(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if limit is not None and len(text) > limit:
        return text[-limit:]
    return text


def input_state() -> dict[str, Any]:
    data = read_json(lgwf_dir() / "context.json", {})
    if isinstance(data, dict):
        state_input = data.get("input")
        if isinstance(state_input, dict):
            return state_input
    return {}


def output_state(updates: dict[str, Any], *, next_key: str | None = None, route_node: str | None = None) -> None:
    payload: dict[str, Any] = {f"{STATE_ROOT}.{key}": value for key, value in updates.items()}
    if next_key is not None:
        if not route_node:
            raise ValueError("route_node is required when next_key is set")
        payload[f"__route__{route_node}"] = next_key
    print(json.dumps(payload, ensure_ascii=False))


def skill_lgwf_py() -> Path:
    configured = os.environ.get("LGWF_CLIENT_ASSIST")
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.name == "lgwf.py":
            return configured_path
        return configured_path / "scripts" / "lgwf.py"
    current = Path(__file__).resolve()
    for parent in current.parents:
        bundled = parent / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
        if bundled.is_file():
            return bundled
    expected = current.parents[4] / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
    raise FileNotFoundError(f"missing bundled lgwf-client-assist: {expected}")


def run_lgwf(args: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(skill_lgwf_py()), *args]
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


def load_self_fix_target() -> dict[str, Any]:
    data = read_json(lgwf_dir() / "self_fix_target.json", {})
    if not isinstance(data, dict):
        raise ValueError(".lgwf/self_fix_target.json must contain a JSON object")
    return data


def load_self_fix_request() -> dict[str, Any]:
    data = read_json(lgwf_dir() / "self_fix_request.json", {})
    if not isinstance(data, dict):
        raise ValueError(".lgwf/self_fix_request.json must contain a JSON object")
    return data


def append_history(event: dict[str, Any]) -> list[dict[str, Any]]:
    path = lgwf_dir() / "self_fix_history.json"
    history = read_json(path, [])
    if not isinstance(history, list):
        history = []
    event = dict(event)
    event.setdefault("ts", datetime.now(UTC).isoformat())
    history.append(event)
    write_json(path, history)
    return history


def attempt_dir(attempt: int) -> Path:
    return lgwf_dir() / "target_runs" / f"attempt-{attempt:03d}"


def current_attempt() -> int:
    target = load_self_fix_target()
    value = target.get("current_attempt", 0)
    return int(value or 0)
