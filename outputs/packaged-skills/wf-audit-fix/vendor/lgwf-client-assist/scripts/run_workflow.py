import argparse
import json
import os
import pathlib
import subprocess
import sys
from typing import TextIO


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lgwf_env_init import bootstrap as bootstrap_module
from lgwf_env_init import existing_workflow as existing_workflow_module
from lgwf_env_init import install as install_module
from lgwf_env_init import launcher as launcher_module
from lgwf_env_init import process_status as process_status_module

# `lgwf.py` shares this directory with the real `lgwf` package name.
# Keep the sibling import path scoped so later runtime imports cannot resolve
# this facade script as the `lgwf` package.
while str(SCRIPT_DIR) in sys.path:
    sys.path.remove(str(SCRIPT_DIR))


class _ProcessExecutionProxy:
    def __init__(self, base):
        self._base = base

    def __getattr__(self, name: str):
        return getattr(self._base, name)

    def call_command(self, command: list[str], **kwargs) -> int:
        return subprocess.call(command, **kwargs)

    def popen_command(self, command: list[str], **kwargs):
        return subprocess.Popen(command, **kwargs)

    def is_process_running(self, pid: int) -> bool:
        return _is_process_running(pid)

    def new_console_flags(self) -> int:
        return getattr(subprocess, "CREATE_NEW_CONSOLE", 0)


def main(
    argv: list[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    skill_root: pathlib.Path | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    _configure_utf8(output)
    _configure_utf8(error_output)
    args = _build_parser().parse_args(argv)
    root = skill_root or pathlib.Path(__file__).resolve().parents[1]
    wheel = install_module.find_bundled_wheel(root)
    support = _runtime_support(wheel)

    if args.doctor:
        install_module.write_doctor_report(args, support, output)
        return 0

    if args.stop_pid:
        _ensure_lgwf_installed(
            wheel,
            force=args.force_install,
            stderr=error_output,
            python_module=support.python,
            skill_root=root,
        )
        return process_status_module.stop_process_tree(args.stop_pid, error_output, support)
    if args.status_pid:
        _ensure_lgwf_installed(
            wheel,
            force=args.force_install,
            stderr=error_output,
            python_module=support.python,
            skill_root=root,
        )
        return process_status_module.write_process_status(args.status_pid, args.work_dir, output, support)

    validation_error = _validate_workflow_args(args)
    if validation_error:
        print(validation_error, file=error_output)
        return 2
    if not args.work_dir:
        print("--work-dir is required unless --doctor is used", file=error_output)
        return 2
    if args.show_console and args.output_json:
        print("--show-console cannot be combined with --output-json", file=error_output)
        return 2
    if args.background and args.output_json:
        print("--background cannot be combined with --output-json", file=error_output)
        return 2
    if args.background and args.show_console:
        print("--background cannot be combined with --show-console", file=error_output)
        return 2
    if args.rerun_existing and args.continue_existing:
        print("--rerun-existing cannot be combined with --continue-existing", file=error_output)
        return 2
    if args.resume_existing and (args.rerun_existing or args.continue_existing):
        print("--resume-existing cannot be combined with --rerun-existing or --continue-existing", file=error_output)
        return 2
    if args.workflow_lgwf:
        args.workflow_lgwf = str(_resolve_workflow_path(args.workflow_lgwf))
    input_json_exit_code = _resolve_input_json_arg(args, error_output)
    if input_json_exit_code is not None:
        return input_json_exit_code

    existing_exit_code = existing_workflow_module.handle_existing_workflow_data(args, output, error_output, support)
    if existing_exit_code is not None:
        return existing_exit_code

    process_status_module.stop_work_dir_processes(pathlib.Path(args.work_dir), error_output, support)

    _ensure_lgwf_installed_timed(
        wheel,
        force=args.force_install,
        stderr=error_output,
        support=support,
        skill_root=root,
    )

    if args.workflow_lgwf:
        workspace_cwd = _workflow_workspace_cwd(args.workflow_lgwf)
        if args.resume_existing:
            launcher_module.delete_workflow_package_snapshot(args.work_dir, support)
        copy_exit_code, snapshot = launcher_module.copy_workflow_package(
            args.workflow_lgwf,
            args.work_dir,
            error_output,
            support,
        )
        if copy_exit_code != 0 or snapshot is None:
            return copy_exit_code
        snapshot_lgwf = snapshot["workflow_lgwf"]
        workflow_json = pathlib.Path(snapshot["workflow_json"])
        audit_exit_code = launcher_module.audit_lgwf(snapshot_lgwf, error_output, support, cwd=workspace_cwd)
        if audit_exit_code != 0:
            return audit_exit_code
        compile_exit_code = launcher_module.compile_lgwf(snapshot_lgwf, workflow_json, error_output, support, cwd=workspace_cwd)
        if compile_exit_code != 0:
            return compile_exit_code
        command = launcher_module.runtime_command(str(workflow_json), args, support)
        if args.background:
            return launcher_module.run_in_background(command, args, workflow_json, output, error_output, support, cwd=workspace_cwd)
        if args.output_json:
            return launcher_module.run_and_write_output_json(command, pathlib.Path(args.output_json), error_output, support, cwd=workspace_cwd)
        return launcher_module.run_runtime_command(command, args, error_output, support, cwd=workspace_cwd)

    command = launcher_module.runtime_command(args.workflow_json, args, support)
    if args.background:
        return launcher_module.run_in_background(command, args, pathlib.Path(args.workflow_json), output, error_output, support)
    if args.output_json:
        return launcher_module.run_and_write_output_json(command, pathlib.Path(args.output_json), error_output, support)

    return launcher_module.run_runtime_command(command, args, error_output, support)


def _workflow_workspace_cwd(workflow_lgwf: str) -> pathlib.Path:
    workflow_path = _resolve_workflow_path(workflow_lgwf)
    parts = workflow_path.parts
    if "workflows" in parts:
        index = parts.index("workflows")
        if index > 0:
            return pathlib.Path(*parts[:index])
    return workflow_path.parent


def _resolve_workflow_path(workflow_lgwf: str) -> pathlib.Path:
    workflow_path = pathlib.Path(workflow_lgwf).expanduser()
    if workflow_path.is_absolute():
        return workflow_path.resolve()
    cwd_candidate = (pathlib.Path.cwd() / workflow_path).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    fallback_candidate = (_workflow_fallback_root() / workflow_path).resolve()
    if fallback_candidate.exists() or workflow_path.parts[:1] == ("workflows",):
        return fallback_candidate
    return cwd_candidate


def _workflow_fallback_root() -> pathlib.Path:
    candidates = [
        SCRIPT_DIR.parents[2] if len(SCRIPT_DIR.parents) > 2 else None,
        SCRIPT_DIR.parents[1] if len(SCRIPT_DIR.parents) > 1 else None,
        SCRIPT_DIR.parent,
    ]
    for candidate in candidates:
        if candidate is not None and (candidate / "workflows").is_dir():
            return candidate.resolve()
    return SCRIPT_DIR.parent.resolve()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install bundled LGWF when needed and run a workflow JSON or .lgwf source locally.",
    )
    parser.add_argument("--workflow-json")
    parser.add_argument("--workflow-lgwf")
    parser.add_argument("--work-dir")
    parser.add_argument("--input-json")
    parser.add_argument("--input-json-file")
    parser.add_argument("--record", choices=["true", "false"])
    parser.add_argument("--output-json")
    parser.add_argument("--background", action="store_true", help="Start workflow in the background and print process metadata JSON.")
    parser.add_argument("--log-file", help="Write background workflow stdout/stderr to this log file.")
    parser.add_argument("--pid-file", help="Write background workflow process metadata JSON to this file.")
    parser.add_argument("--stop-pid", type=int, help="Stop a background workflow process tree by pid.")
    parser.add_argument("--status-pid", type=int, help="Print background workflow status JSON by pid.")
    parser.add_argument("--request-id", help="Human approval request id for controller operations.")
    parser.add_argument(
        "--rerun-existing",
        action="store_true",
        help="When work-dir contains previous .lgwf data, delete it and start a new workflow without prompting.",
    )
    parser.add_argument(
        "--continue-existing",
        action="store_true",
        help="When work-dir contains previous .lgwf data, report existing workflow status without starting a new run.",
    )
    parser.add_argument(
        "--resume-existing",
        action="store_true",
        help="When work-dir contains a failed or stopped checkpoint, resume from its saved node boundary.",
    )
    parser.add_argument("--resume-run-id", help="Resume a specific failed checkpoint run id.")
    parser.add_argument(
        "--resume-allow-workflow-changed",
        action="store_true",
        help="Allow checkpoint resume even when the workflow JSON hash changed.",
    )
    parser.add_argument(
        "--resume-orphaned-running",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--auto-human",
        action="store_true",
        help="Automatically approve human approval and review gates for this run.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Report Python, bundled wheel, installation, and optional path status without installing or running.",
    )
    parser.add_argument(
        "--force-install",
        action="store_true",
        help="Accepted for compatibility; bundled wheel installation already replaces the installed lgwf package.",
    )
    parser.add_argument(
        "--show-console",
        action="store_true",
        help="Run the workflow client in a visible console window and keep it open after completion on Windows.",
    )
    return parser


def _resolve_input_json_arg(args: argparse.Namespace, stderr: TextIO) -> int | None:
    if args.input_json and args.input_json_file:
        print("--input-json and --input-json-file cannot be combined", file=stderr)
        return 2
    if args.input_json_file:
        input_json = pathlib.Path(args.input_json_file).read_text(encoding="utf-8-sig")
    elif args.input_json and args.input_json.startswith("@"):
        input_json = pathlib.Path(args.input_json[1:]).read_text(encoding="utf-8-sig")
    else:
        input_json = args.input_json or "{}"
    try:
        json.loads(input_json)
    except json.JSONDecodeError as exc:
        print(f"--input-json must be valid JSON: {exc}", file=stderr)
        return 2
    args.input_json = input_json
    return None

def _validate_workflow_args(args: argparse.Namespace) -> str | None:
    if args.stop_pid or args.status_pid:
        return None
    if args.workflow_json and args.workflow_lgwf:
        return "use exactly one of --workflow-json or --workflow-lgwf"
    if not args.workflow_json and not args.workflow_lgwf:
        return "--workflow-json or --workflow-lgwf is required unless --doctor is used"
    return None


def _configure_utf8(stream: TextIO) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return


def _runtime_support(wheel: pathlib.Path):
    support = bootstrap_module.load_runtime_support(wheel)
    return bootstrap_module.RuntimeSupport(
        wheel=support.wheel,
        python=_python_execution_module(wheel),
        file_ops=support.file_ops,
        process_execution=_ProcessExecutionProxy(support.process_execution),
        timing=support.timing,
        json_io=support.json_io,
        workspace_layout=support.workspace_layout,
    )


def _python_execution_module(wheel: pathlib.Path):
    return bootstrap_module._import_module_from_wheel("lgwf_client.python_execution", wheel, "lgwf_client")


def _ensure_lgwf_installed_timed(
    wheel: pathlib.Path,
    force: bool,
    stderr: TextIO,
    support,
    skill_root: pathlib.Path | None = None,
) -> None:
    timer = support.timing.Timer.start()
    _ensure_lgwf_installed(
        wheel,
        force=force,
        stderr=stderr,
        python_module=support.python,
        skill_root=skill_root,
    )
    print(f"[lgwf] startup step=install_lgwf duration_ms={timer.elapsed_ms()}", file=stderr)


def _ensure_lgwf_installed(
    wheel: pathlib.Path,
    force: bool,
    stderr: TextIO | None = None,
    python_module=None,
    skill_root: pathlib.Path | None = None,
) -> bool:
    support = bootstrap_module.RuntimeSupport(
        wheel=wheel,
        python=python_module or _python_execution_module(wheel),
        file_ops=bootstrap_module._import_module_from_wheel("lgwf_client.file_ops", wheel, "lgwf_client"),
        process_execution=bootstrap_module._import_module_from_wheel("lgwf_client.process_execution", wheel, "lgwf_client"),
        timing=bootstrap_module._import_module_from_wheel("lgwf_client.timing", wheel, "lgwf_client"),
        json_io=bootstrap_module._import_module_from_wheel("lgwf_client.json_io", wheel, "lgwf_client"),
        workspace_layout=bootstrap_module._import_module_from_wheel("lgwf_client.workspace_layout", wheel, "lgwf_client"),
    )
    return install_module.ensure_bundled_lgwf(
        support,
        skill_root or wheel.parent.parent,
        force=force,
        stderr=stderr,
    )


def _is_process_running(pid: int) -> bool:
    return bootstrap_module._import_module_from_wheel(
        "lgwf_client.process_execution",
        install_module.find_bundled_wheel(pathlib.Path(__file__).resolve().parents[1]),
        "lgwf_client",
    ).is_process_running(pid)


if __name__ == "__main__":
    raise SystemExit(main())
