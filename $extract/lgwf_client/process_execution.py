import os
import pathlib
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, IO

import lgwf_tools.timing as timing_module


@dataclass(frozen=True)
class ProcessResult:
    command: list[str] | str
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False


@dataclass(frozen=True)
class ProcessCommand:
    argv: list[str]

    def resolved_for_spawn(self, resolver: "CommandResolver | None" = None) -> list[str]:
        return (resolver or CommandResolver()).resolve(self.argv)


class CommandResolver:
    def resolve(self, command: list[str]) -> list[str]:
        if os.name != "nt":
            return command
        return self._resolve_windows(command)

    def _resolve_windows(self, command: list[str]) -> list[str]:
        if command and command[0].lower() == "codex":
            codex_command = CodexCliResolver().resolve(command)
            if codex_command is not None:
                return codex_command
        return ["cmd.exe", "/c", *command]


class CodexCliResolver:
    def resolve(self, command: list[str]) -> list[str] | None:
        if not command or command[0].lower() != "codex":
            return None
        return _npm_codex_command(command[1:])


def run_command(
    command: list[str],
    *,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int | float | None = None,
    check: bool = False,
    creationflags: int = 0,
) -> ProcessResult:
    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=None if cwd is None else pathlib.Path(cwd),
            env=env,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
            creationflags=creationflags,
        )
        result = ProcessResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=timing_module.elapsed_ms(started_at),
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        result = ProcessResult(
            command=command,
            returncode=-1,
            stdout=_decode_timeout_output(exc.stdout),
            stderr=_decode_timeout_output(exc.stderr),
            duration_ms=timing_module.elapsed_ms(started_at),
            timed_out=True,
        )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.command,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def run_shell(
    command: str,
    *,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int | float | None = None,
) -> ProcessResult:
    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=None if cwd is None else pathlib.Path(cwd),
            env=env,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        return ProcessResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=timing_module.elapsed_ms(started_at),
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        return ProcessResult(
            command=command,
            returncode=-1,
            stdout=_decode_timeout_output(exc.stdout),
            stderr=_decode_timeout_output(exc.stderr),
            duration_ms=timing_module.elapsed_ms(started_at),
            timed_out=True,
        )


def popen_command(
    command: list[str],
    *,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    stdout: int | IO[Any] | None = None,
    stderr: int | IO[Any] | None = None,
    creationflags: int = 0,
) -> subprocess.Popen:
    return subprocess.Popen(
        command,
        cwd=None if cwd is None else str(pathlib.Path(cwd)),
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
    )


def popen_cli_command(
    command: list[str],
    *,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    stdout: int | IO[Any] | None = None,
    stderr: int | IO[Any] | None = None,
    creationflags: int = 0,
    resolver: CommandResolver | None = None,
) -> subprocess.Popen:
    return popen_command(
        ProcessCommand(command).resolved_for_spawn(resolver),
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
    )


def cli_resolution_command(command: list[str]) -> list[str]:
    return CommandResolver().resolve(command)


def _npm_codex_command(args: list[str]) -> list[str] | None:
    codex_cmd = shutil.which("codex.cmd") or shutil.which("codex")
    if codex_cmd is None:
        return None
    codex_cmd_path = pathlib.Path(codex_cmd)
    if codex_cmd_path.suffix.lower() != ".cmd":
        return None
    codex_js = codex_cmd_path.parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    if not codex_js.is_file():
        return None
    bundled_node = codex_cmd_path.parent / "node.exe"
    node = str(bundled_node) if bundled_node.is_file() else "node"
    return [node, str(codex_js), *args]


def call_command(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    creationflags: int = 0,
) -> int:
    return subprocess.call(command, env=env, creationflags=creationflags)


def background_no_window_flags() -> int:
    if os.name != "nt" or not hasattr(subprocess, "CREATE_NO_WINDOW"):
        return 0
    return subprocess.CREATE_NO_WINDOW


def new_console_flags() -> int:
    if os.name != "nt" or not hasattr(subprocess, "CREATE_NEW_CONSOLE"):
        return 0
    return subprocess.CREATE_NEW_CONSOLE


def visible_console_command(command: list[str]) -> list[str]:
    return ["cmd.exe", "/k", *command]


def is_process_running(pid: int) -> bool:
    if os.name == "nt":
        completed = run_command(
            ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
        )
        return str(pid) in completed.stdout
    completed = subprocess.run(["kill", "-0", str(pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.returncode == 0


def stop_process_tree(pid: int) -> ProcessResult:
    if os.name == "nt":
        return run_command(["taskkill.exe", "/PID", str(pid), "/T", "/F"])
    started_at = time.perf_counter()
    try:
        process = subprocess.Popen(["kill", "-TERM", str(pid)])
        returncode = process.wait()
        return ProcessResult(
            command=["kill", "-TERM", str(pid)],
            returncode=returncode,
            stdout="",
            stderr="",
            duration_ms=timing_module.elapsed_ms(started_at),
        )
    except OSError as exc:
        return ProcessResult(
            command=["kill", "-TERM", str(pid)],
            returncode=1,
            stdout="",
            stderr=str(exc),
            duration_ms=timing_module.elapsed_ms(started_at),
        )


def _decode_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value

