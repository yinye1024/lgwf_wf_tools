import argparse
import os
import pathlib
import shutil
import subprocess
import uuid
from typing import Any
from typing import TextIO

from .bootstrap import RuntimeSupport


def _run_module_with_optional_cwd(support: RuntimeSupport, module: str, args: list[str], cwd: pathlib.Path | None):
    try:
        return support.python.run_module(module, args, cwd=cwd)
    except TypeError as exc:
        if "unexpected keyword argument 'cwd'" not in str(exc):
            raise
        return support.python.run_module(module, args)


def runtime_command(workflow_json: str, args: argparse.Namespace, support: RuntimeSupport) -> list[str]:
    python_env = support.python.discover_python()
    command = python_env.module_command(
        "lgwf_client.cli",
        [
            "--workflow-json",
            workflow_json,
            "--work-dir",
            args.work_dir,
            "--input-json",
            args.input_json,
        ],
    )
    if args.record is not None:
        command.extend(["--record", args.record])
    if getattr(args, "resume_run_id", None):
        command.extend(["--resume-run-id", args.resume_run_id])
    if getattr(args, "resume_allow_workflow_changed", False):
        command.append("--resume-allow-workflow-changed")
    if getattr(args, "resume_orphaned_running", False):
        command.append("--resume-orphaned-running")
    if getattr(args, "auto_human", False):
        command.append("--auto-human")
    return command


def compile_lgwf(
    workflow_lgwf: str,
    workflow_json: pathlib.Path,
    stderr: TextIO,
    support: RuntimeSupport,
    cwd: pathlib.Path | None = None,
) -> int:
    timer = support.timing.Timer.start()
    completed = _run_module_with_optional_cwd(
        support,
        "lgwf_dsl.cli",
        ["compile", str(pathlib.Path(workflow_lgwf).expanduser().resolve()), "-o", str(workflow_json)],
        cwd,
    )
    if completed.stdout:
        stderr.write(completed.stdout)
    if completed.stderr:
        stderr.write(completed.stderr)
    print(
        f"[lgwf] startup step=compile_lgwf duration_ms={timer.elapsed_ms()} output={workflow_json}",
        file=stderr,
    )
    return completed.returncode


def copy_workflow_package(
    workflow_lgwf: str,
    work_dir: str,
    stderr: TextIO,
    support: RuntimeSupport,
) -> tuple[int, dict[str, Any] | None]:
    timer = support.timing.Timer.start()
    completed = support.python.run_module(
        "lgwf_client.cli",
        [
            "copy-workflow-package",
            "--workflow-lgwf",
            workflow_lgwf,
            "--work-dir",
            work_dir,
        ],
    )
    if completed.stderr:
        stderr.write(completed.stderr)
    print(
        f"[lgwf] startup step=copy_workflow_package duration_ms={timer.elapsed_ms()}",
        file=stderr,
    )
    if completed.returncode != 0:
        if completed.stdout:
            stderr.write(completed.stdout)
        return completed.returncode, None
    try:
        payload = support.json_io.parse_json_object(completed.stdout, "copy-workflow-package output")
    except ValueError as exc:
        print(f"[lgwf] {exc}", file=stderr)
        return 2, None
    for field in ("workflow_root", "workflow_lgwf", "workflow_json"):
        if not isinstance(payload.get(field), str) or not payload[field]:
            print(f"[lgwf] copy-workflow-package output missing {field}", file=stderr)
            return 2, None
    return 0, payload


def existing_workflow_package_snapshot(work_dir: str, support: RuntimeSupport) -> dict[str, Any] | None:
    workflow_root = support.workspace_layout.lgwf_dir(pathlib.Path(work_dir)) / "workflow"
    workflow_lgwf = workflow_root / "workflow.lgwf"
    if not workflow_lgwf.is_file():
        return None
    return {
        "workflow_root": str(workflow_root.resolve()),
        "workflow_lgwf": str(workflow_lgwf.resolve()),
        "workflow_json": str((workflow_root / "workflow.json").resolve()),
    }


def delete_workflow_package_snapshot(work_dir: str, support: RuntimeSupport) -> None:
    lgwf_dir = support.workspace_layout.lgwf_dir(pathlib.Path(work_dir)).resolve()
    workflow_root = (lgwf_dir / "workflow").resolve()
    if workflow_root.parent != lgwf_dir:
        raise RuntimeError(f"refusing to delete unexpected workflow snapshot path: {workflow_root}")
    if workflow_root.is_dir() and not workflow_root.is_symlink():
        shutil.rmtree(workflow_root)
    elif workflow_root.exists():
        workflow_root.unlink()


def audit_lgwf(
    workflow_lgwf: str,
    stderr: TextIO,
    support: RuntimeSupport,
    cwd: pathlib.Path | None = None,
) -> int:
    timer = support.timing.Timer.start()
    completed = _run_module_with_optional_cwd(
        support,
        "lgwf_dsl.cli",
        ["audit", str(pathlib.Path(workflow_lgwf).expanduser().resolve())],
        cwd,
    )
    if completed.stdout:
        stderr.write(completed.stdout)
    if completed.stderr:
        stderr.write(completed.stderr)
    print(
        f"[lgwf] startup step=audit_lgwf duration_ms={timer.elapsed_ms()}",
        file=stderr,
    )
    return completed.returncode


def run_and_write_output_json(
    command: list[str],
    output_json: pathlib.Path,
    stderr: TextIO,
    support: RuntimeSupport,
    cwd: pathlib.Path | None = None,
) -> int:
    completed = support.python.run_command(command, cwd=cwd)
    if completed.returncode != 0:
        return completed.returncode

    support.file_ops.write_text_atomic(output_json, completed.stdout)
    print(f"[lgwf] final state written to: {output_json}", file=stderr)
    return completed.returncode


def run_in_background(
    command: list[str],
    args: argparse.Namespace,
    workflow_json: pathlib.Path,
    stdout: TextIO,
    stderr: TextIO,
    support: RuntimeSupport,
    cwd: pathlib.Path | None = None,
) -> int:
    timer = support.timing.Timer.start()
    process_dir = support.workspace_layout.processes_dir(pathlib.Path(args.work_dir))
    support.file_ops.ensure_dir(process_dir)
    process_key = uuid.uuid4().hex
    log_file = pathlib.Path(args.log_file) if args.log_file else process_dir / f"{process_key}.log"
    pid_file = pathlib.Path(args.pid_file) if args.pid_file else process_dir / f"{process_key}.pid.json"
    support.file_ops.ensure_dir(log_file.parent)
    support.file_ops.ensure_dir(pid_file.parent)

    log_handle = log_file.open("ab")
    try:
        python_env = support.python.discover_python(command[0])
        process = support.process_execution.popen_command(
            command,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            env=python_env.env(),
            cwd=cwd,
        )
    except Exception:
        log_handle.close()
        raise
    log_handle.close()

    metadata = {
        "pid": process.pid,
        "workflow_json": str(workflow_json),
        "work_dir": str(pathlib.Path(args.work_dir)),
        "log_file": str(log_file),
        "pid_file": str(pid_file),
        "command": command,
    }
    support.file_ops.write_json_atomic(pid_file, metadata, sort_keys=False)
    import lgwf_client.main_agent.sessions as main_agent_sessions_module

    session = main_agent_sessions_module.write_session_manifest(pathlib.Path(args.work_dir), metadata)
    metadata["session_id"] = session["session_id"]
    metadata["session_file"] = session["session_file"]
    support.file_ops.write_json_atomic(pid_file, metadata, sort_keys=False)
    support.json_io.write_json_line(stdout, metadata, sort_keys=False)
    print(
        f"[lgwf] startup step=background_start duration_ms={timer.elapsed_ms()} "
        f"pid={process.pid} log={log_file}",
        file=stderr,
    )
    return 0


def run_runtime_command(
    command: list[str],
    args: argparse.Namespace,
    stderr: TextIO,
    support: RuntimeSupport,
    cwd: pathlib.Path | None = None,
) -> int:
    if not args.show_console:
        python_env = support.python.discover_python(command[0])
        return support.process_execution.call_command(command, env=python_env.env(), cwd=cwd)
    return run_in_visible_console(command, stderr, support)


def run_in_visible_console(command: list[str], stderr: TextIO, support: RuntimeSupport) -> int:
    if os.name != "nt":
        print("[lgwf] --show-console is only supported on Windows; running in the current console", file=stderr)
        python_env = support.python.discover_python(command[0])
        return support.process_execution.call_command(command, env=python_env.env())

    console_command = support.process_execution.visible_console_command(command)
    print("[lgwf] launching workflow process in a visible console window", file=stderr)
    print(f"[lgwf] command: {' '.join(command)}", file=stderr)
    python_env = support.python.discover_python(command[0])
    process = support.process_execution.popen_command(
        console_command,
        creationflags=support.process_execution.new_console_flags(),
        env=python_env.env(),
    )
    print(f"[lgwf] workflow process pid={process.pid}", file=stderr)
    return process.wait()
