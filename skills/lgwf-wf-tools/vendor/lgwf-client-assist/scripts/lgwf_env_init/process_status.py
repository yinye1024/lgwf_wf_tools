import os
import pathlib
import re
from typing import TextIO

from .bootstrap import RuntimeSupport


def write_process_status(pid: int, work_dir: str | None, stdout: TextIO, support: RuntimeSupport) -> int:
    metadata = find_process_metadata(pid, work_dir, support)
    status = process_status(pid, support)
    if metadata:
        status.update(metadata)
        log_file = pathlib.Path(metadata["log_file"])
        status["log_tail"] = read_log_tail(log_file, support)
        status.update(summarize_progress(status["log_tail"]))
        status["pending_human_requests"] = pending_human_requests(pathlib.Path(metadata["work_dir"]), support)
        latest_run = latest_run_record(pathlib.Path(metadata["work_dir"]), support)
        if latest_run:
            status["latest_run"] = latest_run
        codex_status = latest_codex_status(pathlib.Path(metadata["work_dir"]), support)
        if codex_status:
            status["codex"] = codex_status
        status["main_agent_status"] = build_main_agent_status(pid, pathlib.Path(metadata["work_dir"]), metadata)
    status.update(build_display_status(status))
    support.json_io.write_json_line(stdout, status, sort_keys=False)
    return 0


def build_main_agent_status(pid: int, work_dir: pathlib.Path, metadata: dict) -> dict:
    import lgwf_client.main_agent.status as main_agent_status_module

    session_id = metadata.get("session_id")
    return main_agent_status_module.get_main_agent_status(
        work_dir,
        pid=pid,
        session_id=session_id if isinstance(session_id, str) else None,
    )


def find_process_metadata(pid: int, work_dir: str | None, support: RuntimeSupport) -> dict | None:
    roots: list[pathlib.Path] = []
    if work_dir:
        roots.append(support.workspace_layout.processes_dir(pathlib.Path(work_dir)))
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.glob("*.pid.json"):
            try:
                data = support.file_ops.read_json_object(path, label="process metadata")
            except (OSError, ValueError):
                continue
            if data.get("pid") == pid:
                return data
    return None


def latest_process_metadata(work_dir: pathlib.Path, support: RuntimeSupport) -> dict | None:
    process_dir = support.workspace_layout.processes_dir(work_dir)
    if not process_dir.is_dir():
        return None
    pid_files = sorted(process_dir.glob("*.pid.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in pid_files:
        try:
            data = support.file_ops.read_json(path)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return None


def process_status(pid: int, support: RuntimeSupport) -> dict:
    running = is_process_running(pid, support)
    return {"pid": pid, "running": running}


def is_process_running(pid: int, support: RuntimeSupport) -> bool:
    return support.process_execution.is_process_running(pid)


def read_log_tail(path: pathlib.Path, support: RuntimeSupport, max_lines: int = 80) -> list[str]:
    try:
        content = support.file_ops.read_text(path, errors="replace")
    except OSError:
        return []
    return content.splitlines()[-max_lines:]


def summarize_progress(lines: list[str]) -> dict:
    summary: dict[str, object] = {
        "phase": "unknown",
        "current_node": None,
        "current_capability": None,
        "last_result": None,
        "last_completed": None,
        "last_error": None,
        "human_request_id": None,
    }
    for line in lines:
        if "[workflow] started" in line:
            summary["phase"] = "running"
        if "[workflow] node started" in line or "[workflow] node waiting" in line or "[workflow] node completed" in line:
            node = extract_progress_field(line, "id")
            capability = extract_progress_field(line, "capability")
            if node:
                summary["current_node"] = node
            if capability:
                summary["current_capability"] = capability
                if capability == "flow.human_approval" and "node waiting" in line:
                    summary["phase"] = "waiting_human"
                elif capability == "flow.human_review" and "node waiting" in line:
                    summary["phase"] = "waiting_review"
                else:
                    summary["phase"] = "running"
            if "node completed" in line:
                summary["last_result"] = line
                summary["last_completed"] = parse_completed_progress(line)
        if "[workflow] human approval pending" in line:
            summary["phase"] = "waiting_human"
            request_id = extract_progress_field(line, "request_id")
            if request_id:
                summary["human_request_id"] = request_id
        if "[workflow] human review pending" in line:
            summary["phase"] = "waiting_review"
            request_id = extract_progress_field(line, "request_id")
            if request_id:
                summary["human_request_id"] = request_id
        if "[workflow] failed" in line or " failed:" in line:
            summary["phase"] = "failed"
            summary["last_error"] = line
        if "[workflow] completed" in line:
            summary["phase"] = "completed"
            summary["last_result"] = line
    return summary


def build_display_status(status: dict) -> dict:
    raw_phase = status.get("phase")
    if raw_phase in {None, "unknown"}:
        phase = "running" if status.get("running") else "stopped"
    else:
        phase = str(raw_phase)
    current_node = status.get("current_node")
    current_capability = status.get("current_capability")
    human_request_id = status.get("human_request_id")
    pending_human_requests = status.get("pending_human_requests")
    last_completed = status.get("last_completed")
    waiting_for = waiting_for_status(phase, current_capability, pending_human_requests)
    display = {
        "phase": phase,
        "current": {
            "node": current_node,
            "capability": current_capability,
            "codex": codex_display(status.get("codex")),
        },
        "waiting_for": waiting_for,
        "human_request_id": human_request_id,
        "pending_human_count": len(pending_human_requests) if isinstance(pending_human_requests, list) else 0,
        "last_completed": last_completed,
        "last_error": status.get("last_error"),
    }
    return {
        "display": display,
        "status_line": format_status_line(display),
        "status_text": format_status_text(display),
    }


def waiting_for_status(phase: str, capability: object, pending_human_requests: object) -> str | None:
    if phase == "waiting_human" or pending_human_requests:
        return "人工确认回复"
    if phase in {"completed", "failed", "stopped"}:
        return None
    if capability == "exec.codex_prompt":
        return "Codex 节点完成"
    if capability == "exec.run_python":
        return "Python 脚本完成"
    if capability == "exec.run_shell":
        return "Shell 命令完成"
    if isinstance(capability, str) and capability:
        return f"{capability} 完成"
    return "workflow 继续推进"


def format_status_line(display: dict) -> str:
    current = display.get("current") if isinstance(display.get("current"), dict) else {}
    phase = str(display.get("phase") or "unknown")
    parts = [phase_label(phase)]
    node = current.get("node")
    capability = current.get("capability")
    if node and capability:
        parts.append(f"{node}（{capability}）")
    elif node:
        parts.append(str(node))
    waiting_for = display.get("waiting_for")
    if waiting_for:
        parts.append(f"等待：{waiting_for}")
    codex = current.get("codex")
    if isinstance(codex, dict) and codex.get("instruction_id"):
        parts.append(f"Codex：{codex.get('instruction_id')}")
        if codex.get("output_json_path"):
            parts.append(f"输出：{codex.get('output_json_path')}")
    human_request_id = display.get("human_request_id")
    if human_request_id:
        parts.append(f"确认请求：{human_request_id}")
    last_completed = display.get("last_completed")
    if isinstance(last_completed, dict) and last_completed.get("node"):
        completed = f"最近完成：{last_completed.get('node')}"
        if last_completed.get("duration_ms") is not None:
            completed += f"，用时 {format_duration_ms(last_completed.get('duration_ms'))}"
        parts.append(completed)
    last_error = display.get("last_error")
    if last_error:
        parts.append(f"错误：{last_error}")
    return "；".join(str(part) for part in parts)


def format_status_text(display: dict) -> str:
    current = display.get("current") if isinstance(display.get("current"), dict) else {}
    phase = str(display.get("phase") or "unknown")
    lines = [f"状态：{phase_label(phase)}"]
    node = current.get("node")
    capability = current.get("capability")
    if node and capability:
        lines.append(f"正在执行：{node}（{capability}）")
    elif node:
        lines.append(f"正在执行：{node}")
    waiting_for = display.get("waiting_for")
    if waiting_for:
        lines.append(f"正在等待：{waiting_for}")
    codex = current.get("codex")
    if isinstance(codex, dict) and codex.get("instruction_id"):
        lines.append(f"Codex instruction：{codex.get('instruction_id')}")
        if codex.get("track_dir"):
            lines.append(f"Codex track：{codex.get('track_dir')}")
        if codex.get("stdout_path"):
            lines.append(f"Codex stdout：{codex.get('stdout_path')}")
        if codex.get("stderr_path"):
            lines.append(f"Codex stderr：{codex.get('stderr_path')}")
        if codex.get("output_json_path"):
            lines.append(f"Codex output JSON：{codex.get('output_json_path')}")
        if codex.get("last_file_update_unix") is not None:
            lines.append(f"Codex 最后文件更新时间：{codex.get('last_file_update_unix')}")
    human_request_id = display.get("human_request_id")
    if human_request_id:
        lines.append(f"确认请求：{human_request_id}")
    last_completed = display.get("last_completed")
    if isinstance(last_completed, dict) and last_completed.get("node"):
        lines.append(f"最近完成：{format_last_completed(last_completed)}")
    last_error = display.get("last_error")
    if last_error:
        lines.append(f"最近错误：{last_error}")
    lines.append(f"下一步：{next_step_text(phase)}")
    return "\n".join(lines)


def phase_label(phase: str) -> str:
    labels = {
        "running": "运行中",
        "waiting_human": "等待人工确认",
        "completed": "已完成",
        "failed": "已失败",
        "stopped": "已停止",
        "unknown": "状态未知",
    }
    return labels.get(phase, phase)


def next_step_text(phase: str) -> str:
    if phase == "waiting_human":
        return "向用户展示确认请求，等待 approve 或 reject。"
    if phase == "running":
        return "继续轮询，不要重启 workflow。"
    if phase == "completed":
        return "读取 run summary 和 changed files。"
    if phase == "failed":
        return "读取错误日志和 run summary。"
    return "继续查询状态或检查日志。"


def format_last_completed(last_completed: dict) -> str:
    parts = [str(last_completed.get("node"))]
    capability = last_completed.get("capability")
    if capability:
        parts.append(f"能力 {capability}")
    duration_ms = last_completed.get("duration_ms")
    if duration_ms is not None:
        parts.append(f"用时 {format_duration_ms(duration_ms)}")
    ok = last_completed.get("ok")
    if ok is not None:
        parts.append(f"结果 {format_ok(ok)}")
    artifact_count = last_completed.get("artifact_count")
    warning_count = last_completed.get("warning_count")
    if artifact_count is not None:
        parts.append(f"产物 {artifact_count}")
    if warning_count is not None:
        parts.append(f"警告 {warning_count}")
    return "，".join(parts)


def format_duration_ms(duration_ms: object) -> str:
    if not isinstance(duration_ms, int):
        return str(duration_ms)
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    seconds = duration_ms // 1000
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    if minutes:
        return f"{minutes}分{remaining_seconds}秒"
    return f"{seconds}秒"


def format_ok(ok: object) -> str:
    if str(ok).lower() == "true":
        return "成功"
    if str(ok).lower() == "false":
        return "失败"
    return str(ok)


def parse_completed_progress(line: str) -> dict:
    result = {
        "node": extract_progress_field(line, "id"),
        "capability": extract_progress_field(line, "capability"),
        "duration_ms": extract_int_progress_field(line, "duration_ms"),
        "ok": extract_progress_field(line, "ok"),
        "exit_code": extract_progress_field(line, "exit_code"),
        "artifact_count": extract_int_progress_field(line, "artifact_count"),
        "warning_count": extract_int_progress_field(line, "warning_count"),
    }
    token_usage = extract_token_usage(line)
    if token_usage is not None:
        result["token_usage"] = token_usage
    return result


def extract_progress_field(line: str, key: str) -> str | None:
    match = re.search(rf"{re.escape(key)}=([^\s]+)", line)
    if not match:
        return None
    return match.group(1)


def extract_int_progress_field(line: str, key: str) -> int | None:
    value = extract_progress_field(line, key)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def extract_token_usage(line: str) -> dict | None:
    total = extract_int_progress_field(line, "token_total")
    if total is None:
        return None
    return {
        "input_tokens": extract_int_progress_field(line, "token_input") or 0,
        "output_tokens": extract_int_progress_field(line, "token_output") or 0,
        "total_tokens": total,
        "cached_input_tokens": extract_int_progress_field(line, "token_cached") or 0,
        "reasoning_output_tokens": extract_int_progress_field(line, "token_reasoning") or 0,
    }


def pending_human_requests(work_dir: pathlib.Path, support: RuntimeSupport) -> list[dict]:
    human_dir = support.workspace_layout.human_dir(work_dir)
    if not human_dir.is_dir():
        return []
    requests: list[dict] = []
    for request_path in sorted(human_dir.glob("*.request.json")):
        request_id = request_path.name.removesuffix(".request.json")
        response_path = support.workspace_layout.human_response_path(work_dir, request_id)
        if response_path.exists():
            continue
        try:
            data = support.file_ops.read_json_object(request_path, label="human request")
        except (OSError, ValueError):
            continue
        requests.append(
            {
                "request_id": request_id,
                "prompt": data.get("prompt"),
                "created_at": data.get("created_at"),
                "context": data.get("context"),
                "approval_mode": data.get("approval_mode"),
            }
        )
    return requests


def latest_run_record(work_dir: pathlib.Path, support: RuntimeSupport) -> dict | None:
    runs_dir = support.workspace_layout.runs_dir(work_dir)
    if not runs_dir.is_dir():
        return None
    records = [path for path in runs_dir.glob("*/record.json")]
    if not records:
        return None
    latest = max(records, key=lambda path: path.stat().st_mtime)
    try:
        data = support.file_ops.read_json_object(latest, label="run record")
    except (OSError, ValueError):
        return None
    return {
        "run_id": data.get("run_id"),
        "status": data.get("status"),
        "workflow": data.get("workflow"),
        "change_summary": data.get("change_summary"),
        "has_trace": support.workspace_layout.run_trace_path(work_dir, data.get("run_id")).is_file()
        if isinstance(data.get("run_id"), str)
        else False,
    }


def latest_codex_status(work_dir: pathlib.Path, support: RuntimeSupport) -> dict | None:
    path = support.workspace_layout.codex_status_path(work_dir)
    if not path.is_file():
        return None
    try:
        data = support.file_ops.read_json_object(path, label="codex status")
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return with_codex_process_liveness(data, support)


def with_codex_process_liveness(data: dict, support: RuntimeSupport) -> dict:
    enriched = dict(data)
    for key in ("runtime_process", "codex_process"):
        process = enriched.get(key)
        if not isinstance(process, dict):
            continue
        pid = process.get("pid")
        if isinstance(pid, int) and pid > 0:
            process = dict(process)
            process["alive"] = support.process_execution.is_process_running(pid)
            enriched[key] = process
    return enriched


def codex_display(codex: object) -> dict | None:
    if not isinstance(codex, dict):
        return None
    track_files = codex.get("track_files") if isinstance(codex.get("track_files"), dict) else {}
    stdout = track_files.get("stdout") if isinstance(track_files.get("stdout"), dict) else {}
    stderr = track_files.get("stderr") if isinstance(track_files.get("stderr"), dict) else {}
    output_json = codex.get("output_json") if isinstance(codex.get("output_json"), dict) else {}
    codex_process = codex.get("codex_process") if isinstance(codex.get("codex_process"), dict) else {}
    return {
        "status": codex.get("status"),
        "instruction_id": codex.get("current_instruction_id"),
        "track_dir": codex.get("track_dir"),
        "stdout_path": stdout.get("path") if isinstance(stdout, dict) else None,
        "stderr_path": stderr.get("path") if isinstance(stderr, dict) else None,
        "output_json_path": output_json.get("path") if isinstance(output_json, dict) else None,
        "last_file_update_unix": codex.get("last_file_update_unix"),
        "codex_process_alive": codex_process.get("alive") if isinstance(codex_process, dict) else None,
    }


def stop_process_tree(pid: int, stderr: TextIO, support: RuntimeSupport) -> int:
    completed = support.process_execution.stop_process_tree(pid)
    if completed.stdout:
        stderr.write(completed.stdout)
    if completed.stderr:
        stderr.write(completed.stderr)
    return completed.returncode


def stop_work_dir_processes(work_dir: pathlib.Path, stderr: TextIO, support: RuntimeSupport) -> list[int]:
    process_ids = _known_work_dir_process_ids(work_dir, support)
    stopped: list[int] = []
    seen: set[int] = set()
    for pid in process_ids:
        if pid in seen or pid == os.getpid():
            continue
        seen.add(pid)
        if not is_process_running(pid, support):
            continue
        completed = support.process_execution.stop_process_tree(pid)
        if completed.stdout:
            stderr.write(completed.stdout)
        if completed.stderr:
            stderr.write(completed.stderr)
        if completed.returncode == 0:
            stopped.append(pid)
            print(f"[lgwf] stopped old workflow cli process pid={pid} work_dir={work_dir}", file=stderr)
    return stopped


def _known_work_dir_process_ids(work_dir: pathlib.Path, support: RuntimeSupport) -> list[int]:
    process_ids: list[int] = []
    process_dir = support.workspace_layout.processes_dir(work_dir)
    if not process_dir.is_dir():
        return process_ids
    for pid_file in process_dir.glob("*.pid.json"):
        try:
            data = support.file_ops.read_json_object(pid_file, label="process metadata")
        except (OSError, ValueError):
            continue
        pid = data.get("pid")
        if isinstance(pid, int):
            process_ids.append(pid)
    process_ids.extend(_windows_cli_process_ids_for_work_dir(work_dir, support))
    return process_ids


def _windows_cli_process_ids_for_work_dir(work_dir: pathlib.Path, support: RuntimeSupport) -> list[int]:
    if os.name != "nt":
        return []
    target = str(work_dir.expanduser().resolve())
    escaped_target = target.replace("'", "''")
    current_pid = os.getpid()
    command = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        (
            f"$target = '{escaped_target}'; "
            f"$current = {current_pid}; "
            "Get-CimInstance Win32_Process | "
            "Where-Object { "
            "$_.Name -like '*python*' -and "
            "$_.ProcessId -ne $current -and "
            "$_.ParentProcessId -ne $current -and "
            "$_.CommandLine -like '*lgwf_client.cli*' -and "
            "$_.CommandLine -like '*--work-dir*' -and "
            "$_.CommandLine -like \"*$target*\" "
            "} | ForEach-Object { $_.ProcessId }"
        ),
    ]
    try:
        completed = support.process_execution.run_command(command)
    except (OSError, AttributeError, TypeError):
        return []
    if completed.returncode != 0:
        return []
    process_ids: list[int] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            process_ids.append(int(line))
        except ValueError:
            continue
    return process_ids
