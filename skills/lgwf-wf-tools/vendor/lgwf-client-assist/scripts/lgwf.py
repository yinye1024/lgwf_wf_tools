import argparse
import os
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
_REVIEW_COMMANDS = {
    "submit": "submit-main-agent-review",
}
_HUMAN_AUTO_COMMANDS = {
    "get": "get-human-gate-policy",
    "set": "set-human-gate-policy",
    "clear": "clear-human-gate-policy",
}
_RUN_COMMANDS = {
    "list": "list-runs",
    "get": "get-run",
    "trace": "get-run-trace",
    "summary": "get-run-summary",
    "changes": "get-run-changes",
    "eval": "eval-run",
    "get-eval": "get-run-eval",
    "eval-suite": "eval-suite",
    "get-eval-suite": "get-run-eval-suite",
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
        if module_runner is not None:
            return run_module("lgwf_dsl.cli", ["audit", *args])
        return _run_audit(args, output, error_output, skill_root)
    if command == "compile":
        if module_runner is not None:
            return run_module("lgwf_dsl.cli", ["compile", *args])
        return _run_compile(args, output, error_output, skill_root)
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
    if command == "review":
        return _run_group(args, _REVIEW_COMMANDS, run_module, error_output, "review")
    if command == "human-auto":
        return _run_group(args, _HUMAN_AUTO_COMMANDS, run_module, error_output, "human-auto")
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
    _configure_codex_defaults(root)

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


def _run_audit(
    argv: list[str],
    stdout: TextIO,
    stderr: TextIO,
    skill_root: pathlib.Path | None,
) -> int:
    root = _resolve_runtime_skill_root(skill_root or pathlib.Path(__file__).resolve().parents[1])
    _configure_codex_defaults(root)
    wheel = install_module.find_bundled_wheel(root)
    support = bootstrap_module.load_runtime_support(wheel)
    install_module.ensure_bundled_lgwf(
        support,
        root,
        force=False,
        stderr=stderr,
    )
    cwd = _workflow_workspace_cwd(argv[0]) if argv else None
    completed = support.python.run_module("lgwf_dsl.cli", ["audit", *_normalize_workflow_arg(argv)], cwd=cwd)
    if completed.stdout:
        stdout.write(completed.stdout)
    if completed.stderr:
        stderr.write(completed.stderr)
    return completed.returncode


def _run_compile(
    argv: list[str],
    stdout: TextIO,
    stderr: TextIO,
    skill_root: pathlib.Path | None,
) -> int:
    root = _resolve_runtime_skill_root(skill_root or pathlib.Path(__file__).resolve().parents[1])
    _configure_codex_defaults(root)
    wheel = install_module.find_bundled_wheel(root)
    support = bootstrap_module.load_runtime_support(wheel)
    install_module.ensure_bundled_lgwf(
        support,
        root,
        force=False,
        stderr=stderr,
    )
    cwd = _workflow_workspace_cwd(argv[0]) if argv else None
    completed = support.python.run_module("lgwf_dsl.cli", ["compile", *_normalize_workflow_arg(argv)], cwd=cwd)
    if completed.stdout:
        stdout.write(completed.stdout)
    if completed.stderr:
        stderr.write(completed.stderr)
    return completed.returncode


def _workflow_workspace_cwd(workflow_lgwf: str) -> pathlib.Path:
    workflow_path = _resolve_workflow_path(workflow_lgwf)
    parts = workflow_path.parts
    if "workflows" in parts:
        index = parts.index("workflows")
        if index > 0:
            return pathlib.Path(*parts[:index])
    return workflow_path.parent


def _normalize_workflow_arg(argv: list[str]) -> list[str]:
    if not argv:
        return []
    return [str(_resolve_workflow_path(argv[0])), *argv[1:]]


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


def _configure_codex_defaults(root: pathlib.Path) -> None:
    config_path = root / "assets" / "codex-defaults.json"
    if config_path.is_file():
        os.environ["LGWF_CODEX_DEFAULTS_CONFIG"] = str(config_path)


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
        "usage: lgwf.py {doctor,audit,compile,schema,run,status,stop,wait,approval,review,human-auto,runs,tool,codex} ...\n"
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
