from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ARTIFACT_NAMES = {
    "run",
    "observation",
    "approval",
    "diagnosis",
    "plan",
    "review",
    "workspace",
    "apply",
    "change_audit",
    "verification",
    "promote",
    "decision",
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def repair_root(lgwf_root: Path) -> Path:
    return lgwf_root / "target_repair"


def current_dir(lgwf_root: Path) -> Path:
    return repair_root(lgwf_root) / "current"


def current_workspace_dir(lgwf_root: Path) -> Path:
    return current_dir(lgwf_root) / "workspace"


def iterations_dir(lgwf_root: Path) -> Path:
    return repair_root(lgwf_root) / "iterations"


def _read(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _loop_path(lgwf_root: Path) -> Path:
    return repair_root(lgwf_root) / "loop.json"


def _iterations_path(lgwf_root: Path) -> Path:
    return repair_root(lgwf_root) / "iterations.json"


def load_loop(lgwf_root: Path) -> dict[str, Any]:
    data = _read(_loop_path(lgwf_root), {})
    return data if isinstance(data, dict) else {}


def load_current_artifact(lgwf_root: Path, name: str, default: Any = None) -> Any:
    if name not in ARTIFACT_NAMES:
        raise ValueError(f"unknown target repair artifact: {name}")
    return _read(current_dir(lgwf_root) / f"{name}.json", default)


def write_current_artifact(lgwf_root: Path, name: str, data: Any) -> Any:
    if name not in ARTIFACT_NAMES:
        raise ValueError(f"unknown target repair artifact: {name}")
    _write(current_dir(lgwf_root) / f"{name}.json", data)
    state = load_loop(lgwf_root)
    if state:
        state["phase"] = name
        state["updated_at"] = _now()
        _write(_loop_path(lgwf_root), state)
    return data


def start_iteration(lgwf_root: Path, target: dict[str, Any]) -> dict[str, Any]:
    root = repair_root(lgwf_root)
    root.mkdir(parents=True, exist_ok=True)
    iterations_dir(lgwf_root).mkdir(parents=True, exist_ok=True)
    if not _iterations_path(lgwf_root).exists():
        _write(_iterations_path(lgwf_root), [])

    current = current_dir(lgwf_root)
    if current.exists():
        shutil.rmtree(current)
    current.mkdir(parents=True, exist_ok=True)

    iteration = int(target.get("current_attempt") or 1)
    state = {
        "loop_id": "target_repair",
        "status": "running",
        "current_iteration": iteration,
        "phase": "run",
        "next": None,
        "stop_reason": None,
        "max_attempts": int(target.get("max_attempts") or 5),
        "started_at": _now(),
        "updated_at": _now(),
    }
    _write(_loop_path(lgwf_root), state)
    return state


def record_decision(lgwf_root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(decision)
    normalized.setdefault("recorded_at", _now())
    write_current_artifact(lgwf_root, "decision", normalized)
    state = load_loop(lgwf_root)
    if state:
        state["phase"] = "decision"
        state["next"] = normalized.get("next") or normalized.get("route")
        state["current_decision"] = normalized
        if normalized.get("category") == "block":
            state["status"] = "blocked"
        elif normalized.get("category") == "finish":
            state["status"] = "finishing"
        state["stop_reason"] = normalized.get("stop_reason")
        state["updated_at"] = _now()
        _write(_loop_path(lgwf_root), state)
    return normalized


def archive_current_iteration(lgwf_root: Path, *, outcome: str) -> dict[str, Any]:
    state = load_loop(lgwf_root)
    iteration = int(state.get("current_iteration") or 1)
    source = current_dir(lgwf_root)
    target = iterations_dir(lgwf_root) / f"{iteration:03d}"
    target.mkdir(parents=True, exist_ok=True)

    for path in source.glob("*.json"):
        shutil.copy2(path, target / path.name)
    workspace = source / "workspace"
    if workspace.exists():
        archived_workspace = target / "workspace"
        if archived_workspace.exists():
            shutil.rmtree(archived_workspace)
        shutil.copytree(workspace, archived_workspace)

    summary = {
        "iteration": iteration,
        "outcome": outcome,
        "archived_at": _now(),
        "artifacts": sorted(path.name for path in target.glob("*.json")),
    }
    iterations = _read(_iterations_path(lgwf_root), [])
    if not isinstance(iterations, list):
        iterations = []
    iterations = [item for item in iterations if not isinstance(item, dict) or item.get("iteration") != iteration]
    iterations.append(summary)
    iterations.sort(key=lambda item: int(item.get("iteration") or 0))
    _write(_iterations_path(lgwf_root), iterations)
    return summary


def finish_loop(lgwf_root: Path, *, status: str, stop_reason: str, report: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_loop(lgwf_root)
    if current_dir(lgwf_root).exists() and state.get("current_iteration"):
        archive_current_iteration(lgwf_root, outcome=status)
    state["status"] = status
    state["stop_reason"] = stop_reason
    state["finished_at"] = _now()
    state["updated_at"] = state["finished_at"]
    _write(_loop_path(lgwf_root), state)

    payload = dict(report or {})
    payload.setdefault("loop_id", "target_repair")
    payload["status"] = status
    payload["stop_reason"] = stop_reason
    payload["iterations"] = _read(_iterations_path(lgwf_root), [])
    payload["finished_at"] = state["finished_at"]
    _write(repair_root(lgwf_root) / "report.json", payload)
    return payload


def check_result(name: str, passed: bool, *, kind: str = "check", required: bool = True, evidence: Any = None) -> dict[str, Any]:
    return {
        "name": name,
        "type": kind,
        "required": required,
        "passed": bool(passed),
        "evidence": evidence or [],
    }
