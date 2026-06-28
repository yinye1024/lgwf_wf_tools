import argparse
import json
import pathlib
import sys
import time
from collections.abc import Callable
from typing import Any, TextIO

import lgwf.client_provider as client_provider_module
import lgwf_tools.file_ops as file_ops_module
import lgwf.human_approval as human_approval_module
import lgwf_tools.json_io as json_io_module
import lgwf.runs.records as run_records_module
import lgwf.runtime as runtime_module
import lgwf_tools.timing as timing_module
import lgwf_tools.workspace_layout as workspace_layout_module
import lgwf_client.client_factory as client_factory_module
import lgwf_client.codex_config as codex_config_module
import lgwf_client.main_agent.approvals as main_agent_approvals_module
import lgwf_client.main_agent.status as main_agent_status_module
import lgwf_client.process_execution as process_execution_module
import lgwf_client.tools.registry as tool_registry_module
import lgwf_client.workflow_package.package_snapshot as package_snapshot_module


WorkflowRunner = Callable[
    [dict[str, Any], dict[str, Any], pathlib.Path, pathlib.Path, bool],
    dict[str, Any],
]


def main(
    argv: list[str] | None = None,
    runner: WorkflowRunner | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    effective_argv = argv if argv is not None else sys.argv[1:]
    if effective_argv and effective_argv[0] in _command_names():
        return _run_command(effective_argv, output, error_output)

    parser = _build_parser()
    args = parser.parse_args(argv)

    timer = timing_module.Timer.start()
    run_id = run_records_module.new_run_id()
    try:
        load_timer = timing_module.Timer.start()
        workflow_json = _resolve_workflow_json(args.workflow_json)
        work_dir = _resolve_work_dir(args.work_dir)
        input_state = _parse_input_json(args.input_json)
        record = _parse_record(args.record)
        workflow = _load_workflow(workflow_json)
        error_output.write(f"[workflow] startup step=load_workflow duration_ms={load_timer.elapsed_ms()} run_id={run_id}\n")

        error_output.write(f"[workflow] started workflow_json={workflow_json} work_dir={work_dir} run_id={run_id}\n")
        if runner is None:
            final_state = run_local_workflow(
                workflow,
                input_state,
                workflow_json.parent,
                work_dir,
                record,
                progress_writer=_stderr_progress_writer(error_output),
                run_id=run_id,
            )
        else:
            final_state = runner(
                workflow,
                input_state,
                workflow_json.parent,
                work_dir,
                record,
            )
        error_output.write(f"[workflow] completed duration_ms={timer.elapsed_ms()} run_id={run_id}\n")
    except Exception as exc:
        error_output.write(f"[workflow] failed duration_ms={timer.elapsed_ms()} run_id={run_id}\n")
        error_output.write(f"{type(exc).__name__}: {exc}\n")
        return 2

    json_io_module.write_json_line(output, final_state)
    return 0


def run_local_workflow(
    workflow: dict[str, Any],
    input_state: dict[str, Any],
    workflow_root: pathlib.Path,
    work_dir: pathlib.Path,
    record: bool,
    progress_writer: Callable[[str], None] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    client_timer = timing_module.Timer.start()
    client = client_factory_module.create_default_client(
        workflow_root=str(workflow_root),
        workspace_root=str(work_dir),
    )
    if progress_writer is not None:
        progress_writer(f"[workflow] startup step=create_client duration_ms={client_timer.elapsed_ms()}")
    with client_provider_module.use_client(client):
        return runtime_module.invoke_dsl(
            workflow,
            input_state,
            workflow_root=workflow_root,
            workspace_root=work_dir,
            record=record,
            progress_writer=progress_writer,
            run_id=run_id,
        )


def _stderr_progress_writer(stderr: TextIO) -> Callable[[str], None]:
    def write(message: str) -> None:
        stderr.write(message)
        stderr.write("\n")
        stderr.flush()

    return write


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m lgwf_client.cli",
        description="Run an LGWF workflow JSON locally in a Python process.",
    )
    parser.add_argument("--workflow-json", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--input-json", default="{}")
    parser.add_argument("--record", choices=["true", "false"], default="true")
    return parser


def _command_names() -> set[str]:
    return {
        "list-runs",
        "get-run-summary",
        "get-changed-files",
        "list-human-requests",
        "get-human-request",
        "respond-human-request",
        "write-human-controller-payload",
        "get-human-controller-payload",
        "submit-human-controller-payload",
        "get-main-agent-status",
        "submit-main-agent-approval",
        "agent-sleep",
        "stop-workflow",
        "copy-workflow-package",
        "tool",
        "codex",
    }


def _run_command(argv: list[str], stdout: TextIO, stderr: TextIO) -> int:
    try:
        parser = _build_command_parser(stderr)
        args = parser.parse_args(argv)
        if args.command == "list-runs":
            payload = _list_runs(_resolve_work_dir(args.work_dir), args.limit)
        elif args.command == "get-run-summary":
            payload = _get_run_summary(_resolve_work_dir(args.work_dir), args.run_id)
        elif args.command == "get-changed-files":
            payload = _get_changed_files(_resolve_work_dir(args.work_dir), args.run_id)
        elif args.command == "list-human-requests":
            payload = {"requests": human_approval_module.list_pending_requests(_resolve_work_dir(args.work_dir))}
        elif args.command == "get-human-request":
            payload = human_approval_module.load_request(_resolve_work_dir(args.work_dir), args.request_id)
        elif args.command == "respond-human-request":
            response = _parse_response_json(args.response_json)
            human_approval_module.write_response(
                _resolve_work_dir(args.work_dir),
                args.request_id,
                response,
                caller=args.caller,
                approval_token=args.approval_token,
            )
            payload = {"request_id": args.request_id, "ok": True}
        elif args.command == "write-human-controller-payload":
            controller_payload = _parse_payload_json(args.payload_json)
            human_approval_module.write_controller_payload(
                _resolve_work_dir(args.work_dir),
                args.request_id,
                controller_payload,
            )
            payload = {"request_id": args.request_id, "ok": True}
        elif args.command == "get-human-controller-payload":
            payload = human_approval_module.load_controller_payload(_resolve_work_dir(args.work_dir), args.request_id)
        elif args.command == "submit-human-controller-payload":
            human_approval_module.submit_controller_payload(
                _resolve_work_dir(args.work_dir),
                args.request_id,
                final_user_confirmed=_parse_boolean_arg(args.final_user_confirmed, "final-user-confirmed"),
            )
            payload = {"request_id": args.request_id, "ok": True}
        elif args.command == "get-main-agent-status":
            payload = main_agent_status_module.get_main_agent_status(
                _resolve_work_dir(args.work_dir),
                pid=args.pid,
                session_id=args.session_id,
            )
        elif args.command == "submit-main-agent-approval":
            value = _parse_optional_value_json(args.value_json)
            payload = main_agent_approvals_module.submit_main_agent_approval(
                _resolve_work_dir(args.work_dir),
                args.request_id,
                decision=args.decision,
                value=value,
                comment=args.comment,
            )
        elif args.command == "agent-sleep":
            payload = _agent_sleep()
        elif args.command == "stop-workflow":
            payload = _stop_workflow(args.pid)
        elif args.command == "copy-workflow-package":
            payload = package_snapshot_module.copy_workflow_package(
                args.workflow_lgwf,
                _resolve_work_dir(args.work_dir),
            )
        elif args.command == "tool":
            if args.tool_command == "list":
                payload = {"tools": tool_registry_module.list_public_tools()}
            elif args.tool_command == "describe":
                payload = {"tool": tool_registry_module.describe_public_tool(args.name)}
            elif args.tool_command == "run":
                options = _parse_payload_json(args.options_json)
                work_dir = _resolve_work_dir(args.work_dir) if args.work_dir else None
                result = tool_registry_module.run_cli_tool(
                    args.name,
                    options,
                    work_dir=work_dir,
                )
                payload = {"ok": True, "tool": args.name, "result": result}
            else:
                raise ValueError(f"Unknown tool command: {args.tool_command}")
        elif args.command == "codex":
            if args.codex_command == "model":
                work_dir = _resolve_work_dir(args.work_dir)
                if args.model_command == "get":
                    payload = codex_config_module.get_codex_model(work_dir)
                elif args.model_command == "set":
                    payload = codex_config_module.set_codex_model(work_dir, args.model)
                elif args.model_command == "reset":
                    payload = codex_config_module.reset_codex_model(work_dir)
                else:
                    raise ValueError(f"Unknown codex model command: {args.model_command}")
            else:
                raise ValueError(f"Unknown codex command: {args.codex_command}")
        else:
            raise ValueError(f"Unknown command: {args.command}")
    except _CommandParseError:
        return 2
    except Exception as exc:
        stderr.write(f"{type(exc).__name__}: {exc}\n")
        return 2

    json_io_module.write_json_line(stdout, payload)
    return 0


class _CommandParseError(Exception):
    pass


class _CommandArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args: Any, error_output: TextIO | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._error_output = error_output

    def error(self, message: str) -> None:
        if self._error_output is None:
            super().error(message)
        self.print_usage(self._error_output)
        self._error_output.write(f"{self.prog}: error: {message}\n")
        raise _CommandParseError(message)


def _build_command_parser(error_output: TextIO | None = None) -> argparse.ArgumentParser:
    parser = _CommandArgumentParser(
        prog="python -m lgwf_client.cli",
        description="Run LGWF workflows and inspect local LGWF artifacts.",
        error_output=error_output,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=lambda *args, **kwargs: _CommandArgumentParser(
            *args,
            error_output=error_output,
            **kwargs,
        ),
    )

    list_runs = subparsers.add_parser("list-runs")
    list_runs.add_argument("--work-dir", required=True)
    list_runs.add_argument("--limit", type=int, default=10)

    get_summary = subparsers.add_parser("get-run-summary")
    get_summary.add_argument("--work-dir", required=True)
    get_summary.add_argument("--run-id", required=True)

    get_changed = subparsers.add_parser("get-changed-files")
    get_changed.add_argument("--work-dir", required=True)
    get_changed.add_argument("--run-id", required=True)

    list_human = subparsers.add_parser("list-human-requests")
    list_human.add_argument("--work-dir", required=True)

    get_human = subparsers.add_parser("get-human-request")
    get_human.add_argument("--work-dir", required=True)
    get_human.add_argument("--request-id", required=True)

    respond_human = subparsers.add_parser("respond-human-request")
    respond_human.add_argument("--work-dir", required=True)
    respond_human.add_argument("--request-id", required=True)
    respond_human.add_argument("--caller", choices=["agent", "human_controller"], default="agent")
    respond_human.add_argument("--approval-token")
    respond_human.add_argument("--response-json", required=True)

    write_controller_payload = subparsers.add_parser("write-human-controller-payload")
    write_controller_payload.add_argument("--work-dir", required=True)
    write_controller_payload.add_argument("--request-id", required=True)
    write_controller_payload.add_argument("--payload-json", required=True)

    get_controller_payload = subparsers.add_parser("get-human-controller-payload")
    get_controller_payload.add_argument("--work-dir", required=True)
    get_controller_payload.add_argument("--request-id", required=True)

    submit_controller_payload = subparsers.add_parser("submit-human-controller-payload")
    submit_controller_payload.add_argument("--work-dir", required=True)
    submit_controller_payload.add_argument("--request-id", required=True)
    submit_controller_payload.add_argument("--final-user-confirmed", choices=["true", "false"], required=True)

    main_agent_status = subparsers.add_parser("get-main-agent-status")
    main_agent_status.add_argument("--work-dir", required=True)
    main_agent_status.add_argument("--pid", type=_positive_pid)
    main_agent_status.add_argument("--session-id")

    submit_main_agent = subparsers.add_parser("submit-main-agent-approval")
    submit_main_agent.add_argument("--work-dir", required=True)
    submit_main_agent.add_argument("--request-id", required=True)
    submit_main_agent.add_argument("--decision", choices=["approve", "reject"], required=True)
    submit_main_agent.add_argument("--value-json")
    submit_main_agent.add_argument("--comment")

    subparsers.add_parser("agent-sleep")

    stop_workflow = subparsers.add_parser("stop-workflow")
    stop_workflow.add_argument("--pid", type=_positive_pid, required=True)

    copy_package = subparsers.add_parser("copy-workflow-package")
    copy_package.add_argument("--workflow-lgwf", required=True)
    copy_package.add_argument("--work-dir", required=True)

    tool = subparsers.add_parser("tool")
    tool_subparsers = tool.add_subparsers(dest="tool_command", required=True)
    tool_subparsers.add_parser("list")
    tool_describe = tool_subparsers.add_parser("describe")
    tool_describe.add_argument("name")
    tool_run = tool_subparsers.add_parser("run")
    tool_run.add_argument("name")
    tool_run.add_argument("--work-dir")
    tool_run.add_argument("--options-json", default="{}")

    codex = subparsers.add_parser("codex")
    codex_subparsers = codex.add_subparsers(dest="codex_command", required=True)
    codex_model = codex_subparsers.add_parser("model")
    codex_model_subparsers = codex_model.add_subparsers(dest="model_command", required=True)
    codex_model_get = codex_model_subparsers.add_parser("get")
    codex_model_get.add_argument("--work-dir", required=True)
    codex_model_set = codex_model_subparsers.add_parser("set")
    codex_model_set.add_argument("--work-dir", required=True)
    codex_model_set.add_argument("--model", required=True)
    codex_model_reset = codex_model_subparsers.add_parser("reset")
    codex_model_reset.add_argument("--work-dir", required=True)

    return parser


def _list_runs(work_dir: pathlib.Path, limit: int) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be a positive integer.")
    runs_dir = workspace_layout_module.runs_dir(work_dir)
    if not runs_dir.is_dir():
        return {"runs": []}
    records = []
    for path in runs_dir.glob("*.json"):
        if path.name.endswith(".changed_files.json"):
            continue
        record = run_records_module.load_run_record(path)
        records.append(
            {
                "run_id": record["run_id"],
                "status": record["status"],
                "started_at": record["started_at"],
                "finished_at": record["finished_at"],
                "workflow": record["workflow"],
                "change_summary": record.get("change_summary", {}),
                "token_summary": record.get("token_summary", {}),
            }
        )
    records.sort(key=lambda item: item["finished_at"], reverse=True)
    return {"runs": records[:limit]}


def _get_run_summary(work_dir: pathlib.Path, run_id: str) -> dict[str, str]:
    record_path = _run_record_path(work_dir, run_id)
    summary_path = workspace_layout_module.run_summary_path(work_dir, run_id)
    if not summary_path.is_file():
        raise ValueError(f"run summary not found: {run_id}")
    return {"run_id": run_id, "summary": file_ops_module.read_text(summary_path)}


def _get_changed_files(work_dir: pathlib.Path, run_id: str) -> dict[str, Any]:
    record_path = _run_record_path(work_dir, run_id)
    changed_path = workspace_layout_module.changed_files_path(work_dir, run_id)
    if not changed_path.is_file():
        raise ValueError(f"changed files artifact not found: {run_id}")
    try:
        data = file_ops_module.read_json(changed_path)
    except file_ops_module.FileOperationError as exc:
        raise ValueError(f"changed files artifact must contain valid JSON: {changed_path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"changed files artifact root must be a JSON object: {changed_path}")
    return data


def _run_record_path(work_dir: pathlib.Path, run_id: str) -> pathlib.Path:
    if not isinstance(run_id, str) or not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
        raise ValueError("run_id must be a non-empty run id without path separators.")
    path = workspace_layout_module.run_record_path(work_dir, run_id)
    if not path.is_file():
        raise ValueError(f"run not found: {run_id}")
    return path


def _parse_response_json(raw: str) -> dict[str, Any]:
    return json_io_module.parse_json_object(raw, "response-json")


def _agent_sleep() -> dict[str, Any]:
    seconds = 5
    time.sleep(seconds)
    return {"ok": True, "slept_seconds": seconds}


def _stop_workflow(pid: int) -> dict[str, Any]:
    completed = process_execution_module.stop_process_tree(pid)
    return {
        "ok": completed.returncode == 0,
        "pid": pid,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _positive_pid(raw: str) -> int:
    try:
        pid = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("pid must be a positive integer.") from exc
    if pid < 1:
        raise argparse.ArgumentTypeError("pid must be a positive integer.")
    return pid


def _parse_payload_json(raw: str) -> dict[str, Any]:
    return json_io_module.parse_json_object(raw, "payload-json")


def _parse_optional_value_json(raw: str | None) -> Any:
    if raw is None:
        return main_agent_approvals_module.MISSING
    return json_io_module.parse_json_object(raw, "value-json")


def _parse_boolean_arg(raw: str, name: str) -> bool:
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise ValueError(f"{name} must be true or false.")


def _resolve_workflow_json(raw_path: str) -> pathlib.Path:
    path = pathlib.Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"workflow-json must be an existing file: {raw_path}")
    return path


def _resolve_work_dir(raw_path: str) -> pathlib.Path:
    path = pathlib.Path(raw_path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise ValueError(f"work-dir must be an existing directory: {raw_path}")
    return path


def _parse_input_json(raw: str) -> dict[str, Any]:
    return json_io_module.parse_json_object(raw, "input-json")


def _parse_record(raw: str) -> bool:
    return raw == "true"


def _load_workflow(path: pathlib.Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"workflow-json must contain valid JSON: {path}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"workflow-json root must be a JSON object: {path}")

    return data


if __name__ == "__main__":
    raise SystemExit(main())

