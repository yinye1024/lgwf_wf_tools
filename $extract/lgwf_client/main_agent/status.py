import pathlib
import re
from typing import Any

import lgwf.human_approval as human_approval_module
import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module
import lgwf_client.process_execution as process_execution_module
import lgwf_client.main_agent.pending_actions as pending_actions_module
import lgwf_client.main_agent.sessions as sessions_module


def get_main_agent_status(
    work_dir: str | pathlib.Path,
    *,
    pid: int | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    root = pathlib.Path(work_dir).expanduser().resolve()
    metadata = _session_or_process_metadata(root, session_id, pid)
    effective_pid = _metadata_pid(metadata) if pid is None else pid
    log_lines = _read_log_tail(metadata)
    progress = _summarize_progress(log_lines)
    pending_requests = human_approval_module.list_pending_requests(root)
    pending_action = _first_pending_action(pending_requests)
    latest_run = _latest_run(root)

    phase = _status_phase(progress, pending_action, effective_pid)
    current_node = progress.get("current_node")
    current_capability = progress.get("current_capability")
    return {
        "phase": phase,
        "session_id": session_id or sessions_module.session_id_for_process(effective_pid),
        "pid": effective_pid,
        "work_dir": str(root),
        "current_node": current_node,
        "current_capability": current_capability,
        "pending_action": pending_action,
        "agent_instruction": _agent_instruction(phase, pending_action),
        "last_completed": progress.get("last_completed"),
        "latest_run": latest_run,
    }


def _session_or_process_metadata(
    root: pathlib.Path,
    session_id: str | None,
    pid: int | None,
) -> dict[str, Any] | None:
    if session_id:
        return sessions_module.load_session_manifest(root, session_id)
    return sessions_module.find_process_metadata(root, pid)


def _metadata_pid(metadata: dict[str, Any] | None) -> int | None:
    if metadata is None:
        return None
    pid = metadata.get("pid")
    if isinstance(pid, int) and pid > 0:
        return pid
    return None


def _read_log_tail(metadata: dict[str, Any] | None, max_lines: int = 80) -> list[str]:
    if metadata is None or not isinstance(metadata.get("log_file"), str):
        return []
    try:
        content = file_ops_module.read_text(pathlib.Path(metadata["log_file"]), errors="replace")
    except OSError:
        return []
    return content.splitlines()[-max_lines:]


def _summarize_progress(lines: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "phase": "unknown",
        "current_node": None,
        "current_capability": None,
        "last_completed": None,
    }
    for line in lines:
        if "[workflow] started" in line:
            summary["phase"] = "running"
        if "[workflow] node started" in line or "[workflow] node waiting" in line or "[workflow] node completed" in line:
            node = _progress_field(line, "id")
            capability = _progress_field(line, "capability")
            if node:
                summary["current_node"] = node
            if capability:
                summary["current_capability"] = capability
                summary["phase"] = "waiting_human" if capability == "flow.human_approval" and "node waiting" in line else "running"
            if "[workflow] node completed" in line:
                summary["last_completed"] = {
                    "node": node,
                    "capability": capability,
                    "duration_ms": _progress_int_field(line, "duration_ms"),
                    "ok": _progress_field(line, "ok"),
                }
                token_usage = _progress_token_usage(line)
                if token_usage is not None:
                    summary["last_completed"]["token_usage"] = token_usage
        if "[workflow] completed" in line:
            summary["phase"] = "completed"
        if "[workflow] failed" in line:
            summary["phase"] = "failed"
    return summary


def _first_pending_action(pending_requests: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not pending_requests:
        return None
    return pending_actions_module.human_approval_action(pending_requests[0])


def _status_phase(progress: dict[str, Any], pending_action: dict[str, Any] | None, pid: int | None) -> str:
    if pending_action is not None:
        return "waiting_human"
    progress_phase = progress.get("phase")
    if progress_phase not in {None, "unknown"}:
        return str(progress_phase)
    if pid is not None and process_execution_module.is_process_running(pid):
        return "running"
    return "stopped"


def _agent_instruction(phase: str, pending_action: dict[str, Any] | None) -> str:
    if pending_action is not None and pending_action.get("type") == "human_approval":
        return "ask_user_approve_or_reject"
    if phase == "running":
        return "poll_workflow_status"
    if phase == "completed":
        return "read_run_summary"
    if phase == "failed":
        return "inspect_failure"
    return "poll_or_start_workflow"


def _latest_run(root: pathlib.Path) -> dict[str, Any] | None:
    runs_dir = workspace_layout_module.runs_dir(root)
    if not runs_dir.is_dir():
        return None
    records = [
        path
        for path in runs_dir.glob("*.json")
        if not path.name.endswith(".changed_files.json")
    ]
    if not records:
        return None
    latest = max(records, key=lambda path: path.stat().st_mtime)
    try:
        data = file_ops_module.read_json(latest)
    except (OSError, ValueError, file_ops_module.FileOperationError):
        return None
    if not isinstance(data, dict):
        return None
    return {
        "run_id": data.get("run_id"),
        "status": data.get("status"),
        "workflow": data.get("workflow"),
        "change_summary": data.get("change_summary"),
        "token_summary": data.get("token_summary"),
    }


def _progress_field(line: str, key: str) -> str | None:
    match = re.search(rf"{re.escape(key)}=([^\s]+)", line)
    if match is None:
        return None
    return match.group(1)


def _progress_int_field(line: str, key: str) -> int | None:
    value = _progress_field(line, key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _progress_token_usage(line: str) -> dict[str, int] | None:
    total = _progress_int_field(line, "token_total")
    if total is None:
        return None
    return {
        "input_tokens": _progress_int_field(line, "token_input") or 0,
        "output_tokens": _progress_int_field(line, "token_output") or 0,
        "total_tokens": total,
        "cached_input_tokens": _progress_int_field(line, "token_cached") or 0,
        "reasoning_output_tokens": _progress_int_field(line, "token_reasoning") or 0,
    }
