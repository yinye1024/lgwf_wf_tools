import argparse
import json
import pathlib
import sys
from collections.abc import Callable
from typing import TextIO


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_workflow as run_workflow_module
from lgwf_env_init import bootstrap as bootstrap_module
from lgwf_env_init import install as install_module

while str(SCRIPT_DIR) in sys.path:
    sys.path.remove(str(SCRIPT_DIR))


ModuleRunner = Callable[[str, list[str]], int]
RunWorkflowMain = Callable[..., int]


_APPROVAL_COMMANDS = {
    "list": "list-human-requests",
    "get": "get-human-request",
    "submit": "submit-main-agent-approval",
    "controller-write": "write-human-controller-payload",
    "controller-get": "get-human-controller-payload",
    "controller-submit": "submit-human-controller-payload",
    "respond": "respond-human-request",
}
_RUN_COMMANDS = {
    "list": "list-runs",
    "summary": "get-run-summary",
    "changed": "get-changed-files",
}


def main(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    run_workflow_main: RunWorkflowMain | None = None,
    module_runner: ModuleRunner | None = None,
    skill_root: pathlib.Path | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        _write_usage(error_output)
        return 2

    command = args.pop(0)
    workflow_main = run_workflow_main or run_workflow_module.main
    run_module = module_runner or _module_runner(output, error_output, skill_root)

    if command == "doctor":
        return workflow_main(
            ["--doctor", *args],
            stdout=output,
            stderr=error_output,
            skill_root=skill_root,
        )
    if command == "install":
        return _run_install(args, stdout=output, stderr=error_output, skill_root=skill_root)
    if command == "run":
        return workflow_main(
            args,
            stdout=output,
            stderr=error_output,
            skill_root=skill_root,
        )
    if command == "status":
        return _run_status(
            args,
            workflow_main=workflow_main,
            module_runner=run_module,
            stdout=output,
            stderr=error_output,
            skill_root=skill_root,
        )
    if command == "audit":
        return run_module("lgwf_dsl.cli", ["audit", *args])
    if command == "compile":
        return run_module("lgwf_dsl.cli", ["compile", *args])
    if command == "schema":
        if module_runner is None and _write_source_schema_if_available(output):
            return 0
        return run_module("lgwf_dsl.cli", ["schema", *args])
    if command == "tool":
        return run_module("lgwf_client.cli", ["tool", *args])
    if command == "codex":
        return run_module("lgwf_client.cli", ["codex", *args])
    if command == "stop":
        return run_module("lgwf_client.cli", ["stop-workflow", *args])
    if command == "wait":
        return run_module("lgwf_client.cli", ["agent-sleep", *args])
    if command == "approval":
        return _run_group(args, _APPROVAL_COMMANDS, run_module, error_output, "approval")
    if command == "runs":
        return _run_group(args, _RUN_COMMANDS, run_module, error_output, "runs")

    error_output.write(f"unknown command: {command}\n")
    _write_usage(error_output)
    return 2


def _run_status(
    argv: list[str],
    *,
    workflow_main: RunWorkflowMain,
    module_runner: ModuleRunner,
    stdout: TextIO,
    stderr: TextIO,
    skill_root: pathlib.Path | None,
) -> int:
    parser = _ArgumentParser(
        prog="lgwf.py status",
        add_help=False,
        error_output=stderr,
    )
    parser.add_argument("--work-dir", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pid", type=int)
    group.add_argument("--session-id")
    try:
        args = parser.parse_args(argv)
    except _ParseError:
        return 2

    if args.pid is not None:
        return workflow_main(
            ["--status-pid", str(args.pid), "--work-dir", args.work_dir],
            stdout=stdout,
            stderr=stderr,
            skill_root=skill_root,
        )
    return module_runner(
        "lgwf_client.cli",
        [
            "get-main-agent-status",
            "--work-dir",
            args.work_dir,
            "--session-id",
            args.session_id,
        ],
    )


def _run_install(
    argv: list[str],
    *,
    stdout: TextIO,
    stderr: TextIO,
    skill_root: pathlib.Path | None,
) -> int:
    parser = _ArgumentParser(
        prog="lgwf.py install",
        add_help=True,
        error_output=stderr,
    )
    parser.add_argument("--force", action="store_true", help="force reinstall even if wheel hash matches")
    parser.add_argument("--json", action="store_true", help="print installation state JSON after install")
    try:
        args = parser.parse_args(argv)
    except _ParseError:
        return 2

    root = _resolve_runtime_skill_root(skill_root or pathlib.Path(__file__).resolve().parents[1])
    wheel = install_module.find_bundled_wheel(root)
    support = bootstrap_module.load_runtime_support(wheel)
    replaced = install_module.ensure_bundled_lgwf(
        support,
        root,
        force=bool(args.force),
        stderr=stderr,
    )
    if args.json:
        state = install_module.load_install_state(root)
        report = {
            **state,
            "wheel_replaced": bool(replaced),
            "installed_version": support.python.installed_package_version("lgwf") or "",
        }
        stdout.write(json.dumps(report, ensure_ascii=False) + "\n")
    return 0


def _run_group(
    argv: list[str],
    commands: dict[str, str],
    module_runner: ModuleRunner,
    stderr: TextIO,
    group_name: str,
) -> int:
    if not argv:
        stderr.write(f"{group_name} subcommand is required\n")
        return 2
    subcommand = argv[0]
    client_command = commands.get(subcommand)
    if client_command is None:
        stderr.write(f"unknown {group_name} subcommand: {subcommand}\n")
        return 2
    return module_runner("lgwf_client.cli", [client_command, *argv[1:]])


def _module_runner(
    stdout: TextIO,
    stderr: TextIO,
    skill_root: pathlib.Path | None,
) -> ModuleRunner:
    root = _resolve_runtime_skill_root(skill_root or pathlib.Path(__file__).resolve().parents[1])

    def run(module_name: str, argv: list[str]) -> int:
        wheel = install_module.find_bundled_wheel(root)
        support = bootstrap_module.load_runtime_support(wheel)
        install_module.ensure_bundled_lgwf(
            support,
            root,
            force=False,
            stderr=stderr,
        )
        completed = support.python.run_module(module_name, argv)
        if completed.stdout:
            stdout.write(completed.stdout)
        if completed.stderr:
            stderr.write(completed.stderr)
        return completed.returncode

    return run


def _resolve_runtime_skill_root(root: pathlib.Path) -> pathlib.Path:
    if _has_bundled_wheel(root):
        return root
    if len(root.parents) >= 3:
        repo_root = root.parents[2]
        dist_root = repo_root / "dist" / "wf_fix" / "lgwf-client-assist"
        if _has_bundled_wheel(dist_root):
            return dist_root
    return root


def _has_bundled_wheel(root: pathlib.Path) -> bool:
    assets = root / "assets"
    return assets.is_dir() and any(assets.glob("lgwf-*.whl"))


class _ParseError(Exception):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, error_output: TextIO, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._error_output = error_output

    def error(self, message: str) -> None:
        if "one of the arguments --pid --session-id is required" in message:
            message = "one of --pid or --session-id is required"
        self._error_output.write(f"{self.prog}: error: {message}\n")
        raise _ParseError(message)


def _write_usage(stream: TextIO) -> None:
    stream.write(
        "usage: lgwf.py {doctor,audit,compile,schema,run,status,stop,wait,approval,runs,tool,codex} ...\n"
    )


def _write_source_schema_if_available(stdout: TextIO) -> bool:
    schema_path = pathlib.Path(__file__).resolve().parents[4] / "src" / "lgwf" / "compiler" / "dsl_schema.json"
    if not schema_path.is_file():
        return False
    stdout.write(schema_path.read_text(encoding="utf-8"))
    stdout.write("\n")
    return True


if __name__ == "__main__":
    raise SystemExit(main())
