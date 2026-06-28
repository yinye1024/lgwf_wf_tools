import importlib.metadata
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, TextIO

import lgwf_client.process_execution as process_execution_module
import lgwf_client.resource_refs as resource_refs_module
import lgwf_client.runners.python_runner.builtin_scripts as builtin_scripts_module
import lgwf_client.types as client_types


LGWF_PYTHON_ENV = "LGWF_PYTHON"


@dataclass(frozen=True)
class PythonEnvironment:
    python_executable: pathlib.Path
    version: str
    prefix: pathlib.Path
    scripts_dir: pathlib.Path

    def command(self, *args: str) -> list[str]:
        return [str(self.python_executable), *args]

    def module_command(self, module: str, args: list[str] | None = None) -> list[str]:
        return self.command("-m", module, *(args or []))

    def script_command(self, script: str | pathlib.Path, args: list[str] | None = None) -> list[str]:
        return self.command(str(pathlib.Path(script)), *(args or []))

    def env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env[LGWF_PYTHON_ENV] = str(self.python_executable)
        env["PATH"] = _prepend_path_entries(
            env.get("PATH", ""),
            [self.python_executable.parent, self.scripts_dir],
        )
        env.setdefault("LANG", "C.UTF-8")
        env.setdefault("LC_ALL", "C.UTF-8")
        if extra:
            env.update(extra)
        return env


@dataclass(frozen=True)
class PythonRunResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int


def discover_python(
    explicit: str | pathlib.Path | None = None,
    search_root: str | pathlib.Path | None = None,
    environ: dict[str, str] | None = None,
) -> PythonEnvironment:
    env = environ if environ is not None else os.environ
    candidates: list[pathlib.Path] = []
    if explicit:
        candidates.append(pathlib.Path(explicit))
    if env.get(LGWF_PYTHON_ENV):
        candidates.append(pathlib.Path(env[LGWF_PYTHON_ENV]))
    candidates.append(pathlib.Path(sys.executable))
    if search_root is not None:
        root = pathlib.Path(search_root).expanduser().resolve()
        for candidate in [root, *root.parents]:
            candidates.extend(
                [
                    candidate / ".venv" / "Scripts" / "python.exe",
                    candidate / ".venv" / "bin" / "python",
                ]
            )

    for candidate in _unique_paths(candidates):
        if candidate.is_file():
            return _environment_for(candidate)
    raise RuntimeError("no usable Python executable found.")


def module_command(
    module: str,
    args: list[str] | None = None,
    python: PythonEnvironment | None = None,
) -> list[str]:
    return (python or discover_python()).module_command(module, args)


def script_command(
    script: str | pathlib.Path,
    args: list[str] | None = None,
    python: PythonEnvironment | None = None,
) -> list[str]:
    return (python or discover_python()).script_command(script, args)


def run_module(
    module: str,
    args: list[str] | None = None,
    *,
    python: PythonEnvironment | None = None,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int | float | None = None,
    check: bool = False,
) -> PythonRunResult:
    resolved_python = python or discover_python()
    return run_command(
        resolved_python.module_command(module, args),
        python=resolved_python,
        cwd=cwd,
        env=env,
        timeout_seconds=timeout_seconds,
        check=check,
    )


def run_script(
    script: str | pathlib.Path,
    args: list[str] | None = None,
    *,
    python: PythonEnvironment | None = None,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int | float | None = None,
    check: bool = False,
) -> PythonRunResult:
    resolved_python = python or discover_python()
    return run_command(
        resolved_python.script_command(script, args),
        python=resolved_python,
        cwd=cwd,
        env=env,
        timeout_seconds=timeout_seconds,
        check=check,
    )


def run_command(
    command: list[str],
    *,
    python: PythonEnvironment | None = None,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    timeout_seconds: int | float | None = None,
    check: bool = False,
) -> PythonRunResult:
    resolved_python = python or discover_python(command[0] if command else None)
    completed = process_execution_module.run_command(
        command,
        cwd=None if cwd is None else pathlib.Path(cwd),
        env=resolved_python.env(env),
        timeout_seconds=timeout_seconds,
        check=False,
    )
    result = PythonRunResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ms=completed.duration_ms,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.command,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def popen_module(
    module: str,
    args: list[str] | None = None,
    *,
    python: PythonEnvironment | None = None,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    stdout: Any = None,
    stderr: Any = None,
    creationflags: int = 0,
) -> subprocess.Popen:
    resolved_python = python or discover_python()
    return process_execution_module.popen_command(
        resolved_python.module_command(module, args),
        cwd=None if cwd is None else str(pathlib.Path(cwd)),
        env=resolved_python.env(env),
        stdout=stdout,
        stderr=stderr,
        creationflags=creationflags,
    )


def ensure_package_installed(
    wheel: pathlib.Path,
    *,
    python: PythonEnvironment | None = None,
    stderr: TextIO | None = None,
) -> PythonRunResult:
    resolved_python = python or discover_python()
    result = run_module(
        "pip",
        ["install", "--upgrade", "--force-reinstall", "--no-deps", str(wheel)],
        python=resolved_python,
    )
    if stderr is not None:
        if result.stdout:
            stderr.write(result.stdout)
        if result.stderr:
            stderr.write(result.stderr)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.command,
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def doctor_report(
    wheel: pathlib.Path,
    *,
    workflow_json: str | pathlib.Path | None = None,
    workflow_lgwf: str | pathlib.Path | None = None,
    work_dir: str | pathlib.Path | None = None,
    python: PythonEnvironment | None = None,
) -> dict[str, str]:
    resolved_python = python or discover_python()
    report = {
        "python": str(resolved_python.python_executable),
        "python_version": resolved_python.version,
        "python_prefix": str(resolved_python.prefix),
        "python_scripts_dir": str(resolved_python.scripts_dir),
        "bundled_wheel": str(wheel),
        "bundled_lgwf_version": wheel_version(wheel) or "<unknown>",
        "installed_lgwf_version": installed_package_version("lgwf") or "<missing>",
        "lgwf_client_importable": str(importlib.util.find_spec("lgwf_client") is not None).lower(),
        "lgwf_dsl_importable": str(importlib.util.find_spec("lgwf_dsl") is not None).lower(),
    }
    if workflow_json:
        path = pathlib.Path(workflow_json)
        report["workflow_json"] = str(path)
        report["workflow_json_exists"] = str(path.is_file()).lower()
    if workflow_lgwf:
        path = pathlib.Path(workflow_lgwf)
        report["workflow_lgwf"] = str(path)
        report["workflow_lgwf_exists"] = str(path.is_file()).lower()
    if work_dir:
        path = pathlib.Path(work_dir)
        report["work_dir"] = str(path)
        report["work_dir_exists"] = str(path.is_dir()).lower()
    return report


def installed_package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def wheel_version(wheel: pathlib.Path) -> str | None:
    match = re.match(r"lgwf-([^-]+)-", wheel.name)
    if not match:
        return None
    return match.group(1)


class PythonExecutionTool:
    """Build and execute Python commands for LGWF client instructions."""

    def __init__(
        self,
        workflow_root: str | pathlib.Path | None = None,
        workspace_root: str | pathlib.Path | None = None,
        python_executable: str | pathlib.Path | None = None,
    ) -> None:
        self._roots = resource_refs_module.ResourceRoots(
            workflow_root=workflow_root,
            workspace_root=workspace_root,
        )
        self._python = discover_python(explicit=python_executable)

    def run_instruction(
        self,
        instruction: client_types.Instruction,
    ) -> client_types.ExecutionResult:
        payload = instruction["payload"]
        args = payload.get("args", [])
        options = payload.get("options")
        builtin_script = payload.get("builtin_script")

        self._validate_payload(args, options, builtin_script)
        cwd = resource_refs_module.resolve_cwd(instruction.get("cwd"), self._roots)
        command = self.build_command(
            cwd=cwd,
            code=payload.get("code"),
            script_path=payload.get("script_path"),
            script_ref=payload.get("script_ref"),
            builtin_script=builtin_script,
            options=options,
            args=args,
            ref_root=instruction.get("ref_root"),
        )
        env = self._env(cwd)
        result = run_command(
            command,
            python=self._python,
            cwd=cwd,
            env=env,
            timeout_seconds=instruction["timeout_seconds"],
        )

        metadata: dict[str, Any] = {
            "cwd": str(cwd),
            "mode": self.mode(
                payload.get("code"),
                payload.get("script_path"),
                payload.get("script_ref"),
                builtin_script,
            ),
            "python_executable": str(self._python.python_executable),
            "duration_ms": result.duration_ms,
        }
        if builtin_script is not None:
            metadata["builtin_script"] = builtin_script
        if options is not None:
            metadata["options"] = options

        return {
            "instruction_id": instruction["id"],
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "artifacts": [],
            "changed_files": [],
            "metadata": metadata,
        }

    def build_command(
        self,
        cwd: pathlib.Path,
        code: Any,
        script_path: Any,
        script_ref: Any,
        builtin_script: Any,
        options: Any,
        args: list[str],
        ref_root: Any = None,
    ) -> list[str]:
        has_code = isinstance(code, str) and bool(code.strip())
        has_script = isinstance(script_path, str) and bool(script_path.strip())
        has_script_ref = script_ref is not None
        has_builtin_script = builtin_script is not None

        if sum([has_code, has_script, has_script_ref, has_builtin_script]) != 1:
            raise ValueError("python instruction payload requires exactly one of code, script_path, script_ref, or builtin_script.")

        if has_code:
            return self._python.command("-c", code, *args)

        if has_builtin_script:
            script = builtin_scripts_module.resolve_builtin_script(builtin_script)
            command_args = args
            if options is not None:
                command_args = ["--options-json", json.dumps(options, ensure_ascii=False), *args]
            return self._python.script_command(script, command_args)

        if has_script_ref:
            script = resource_refs_module.resolve_resource_path(cwd, script_ref, "script_ref", self._roots, ref_root)
        else:
            script = resource_refs_module.resolve_resource_path(cwd, {"path": script_path}, "script_path", self._roots)

        if not script.is_file():
            raise ValueError(f"python instruction script does not exist or is not a file: {script}")

        return self._python.script_command(script, args)

    def mode(
        self,
        code: Any,
        script_path: Any,
        script_ref: Any,
        builtin_script: Any,
    ) -> str:
        if isinstance(code, str) and bool(code.strip()):
            return "code"
        if builtin_script is not None:
            return "builtin_script"
        if script_ref is not None:
            return "script_ref"
        if isinstance(script_path, str) and bool(script_path.strip()):
            return "script_path"
        return "unknown"

    def _validate_payload(self, args: Any, options: Any, builtin_script: Any) -> None:
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            raise ValueError("python instruction payload args must be a list of strings.")
        if options is not None and builtin_script is None:
            raise ValueError("python instruction payload options may only be used with builtin_script.")
        if options is not None and not isinstance(options, dict):
            raise ValueError("python instruction payload options must be an object.")

    def _env(self, cwd: pathlib.Path) -> dict[str, str]:
        return {"LGWF_WORKSPACE_ROOT": str(self._workspace_root(cwd))}

    def _workspace_root(self, cwd: pathlib.Path) -> pathlib.Path:
        workspace_root = pathlib.Path(self._roots.workspace_root).resolve() if self._roots.workspace_root is not None else cwd.resolve()
        if not workspace_root.is_dir():
            raise ValueError(f"python instruction workspace root does not exist or is not a directory: {workspace_root}")
        return workspace_root


def _environment_for(python_executable: pathlib.Path) -> PythonEnvironment:
    executable = python_executable.expanduser().resolve()
    scripts_dir = executable.parent
    prefix = scripts_dir.parent.parent if scripts_dir.name.lower() in {"scripts", "bin"} else executable.parent
    return PythonEnvironment(
        python_executable=executable,
        version=sys.version.split()[0],
        prefix=prefix,
        scripts_dir=scripts_dir,
    )


def _prepend_path_entries(existing_path: str, entries: list[pathlib.Path]) -> str:
    existing_parts = [part for part in existing_path.split(os.pathsep) if part]
    normalized_existing = {os.path.normcase(os.path.abspath(part)) for part in existing_parts}
    new_parts: list[str] = []
    for entry in entries:
        entry_text = str(entry)
        normalized_entry = os.path.normcase(os.path.abspath(entry_text))
        if normalized_entry not in normalized_existing:
            new_parts.append(entry_text)
            normalized_existing.add(normalized_entry)
    return os.pathsep.join([*new_parts, *existing_parts])


def _unique_paths(paths: list[pathlib.Path]) -> list[pathlib.Path]:
    unique: list[pathlib.Path] = []
    seen: set[str] = set()
    for path in paths:
        resolved = path.expanduser().resolve()
        key = os.path.normcase(str(resolved))
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return unique
