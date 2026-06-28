import pathlib
import uuid
from typing import Any

import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module


def write_session_manifest(work_dir: pathlib.Path, metadata: dict[str, Any]) -> dict[str, Any]:
    session_id = _session_id(metadata)
    manifest = dict(metadata)
    manifest["session_id"] = session_id
    path = session_manifest_path(work_dir, session_id)
    file_ops_module.write_json_atomic(path, manifest, sort_keys=False)
    manifest["session_file"] = str(path)
    return manifest


def load_session_manifest(work_dir: pathlib.Path, session_id: str) -> dict[str, Any]:
    path = session_manifest_path(work_dir, session_id)
    if not path.is_file():
        raise ValueError(f"main agent session not found: {session_id}")
    data = file_ops_module.read_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"main agent session must be a JSON object: {session_id}")
    return data


def session_manifest_path(work_dir: pathlib.Path, session_id: str) -> pathlib.Path:
    if not isinstance(session_id, str) or not session_id or "/" in session_id or "\\" in session_id or ".." in session_id:
        raise ValueError("session_id must be a non-empty id without path separators.")
    return pathlib.Path(work_dir).resolve() / ".lgwf" / "main_agent" / "sessions" / f"{session_id}.json"


def find_process_metadata(work_dir: pathlib.Path, pid: int | None) -> dict[str, Any] | None:
    if pid is None:
        return latest_process_metadata(work_dir)
    process_dir = workspace_layout_module.processes_dir(work_dir)
    if not process_dir.is_dir():
        return None
    for path in process_dir.glob("*.pid.json"):
        data = _load_process_metadata(path)
        if data is not None and data.get("pid") == pid:
            return data
    return None


def latest_process_metadata(work_dir: pathlib.Path) -> dict[str, Any] | None:
    process_dir = workspace_layout_module.processes_dir(work_dir)
    if not process_dir.is_dir():
        return None
    paths = sorted(process_dir.glob("*.pid.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in paths:
        data = _load_process_metadata(path)
        if data is not None:
            return data
    return None


def session_id_for_process(pid: int | None) -> str | None:
    if pid is None:
        return None
    return f"pid-{pid}"


def _session_id(metadata: dict[str, Any]) -> str:
    pid = metadata.get("pid")
    if isinstance(pid, int) and pid > 0:
        return session_id_for_process(pid) or f"session-{uuid.uuid4().hex}"
    existing = metadata.get("session_id")
    if isinstance(existing, str) and existing:
        return existing
    return f"session-{uuid.uuid4().hex}"


def _load_process_metadata(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        data = file_ops_module.read_json(path)
    except (OSError, ValueError, file_ops_module.FileOperationError):
        return None
    if isinstance(data, dict):
        return data
    return None
