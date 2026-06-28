import json
import os
import pathlib
import re
import subprocess
import tempfile
import time
from typing import Any

import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module
import lgwf_client.codex_config as codex_config_module
import lgwf_client.python_execution as python_execution_module
import lgwf_client.process_execution as process_execution_module
import lgwf_client.resource_refs as resource_refs_module
import lgwf_client.types as client_types


DEFAULT_CODEX_MODEL = codex_config_module.DEFAULT_CODEX_MODEL
DEFAULT_CODEX_TRANSPORT_ARGS = [
    "--disable",
    "responses_websockets",
    "--disable",
    "responses_websockets_v2",
]
DEFAULT_CODEX_JSON_ARGS = ["--json"]
DEFAULT_CODEX_EXEC_ARGS = ["--skip-git-repo-check", "--sandbox", "danger-full-access"]
HANDOFF_TEMPLATE_PATH = pathlib.Path(__file__).resolve().parents[2] / "build_in_prompts" / "codex_prompt_handoff.md"


class CodexRunner:
    instruction_type: client_types.InstructionType = "codex"

    def __init__(
        self,
        workflow_root: str | pathlib.Path | None = None,
        workspace_root: str | pathlib.Path | None = None,
    ) -> None:
        self._roots = resource_refs_module.ResourceRoots(
            workflow_root=workflow_root,
            workspace_root=workspace_root,
        )

    def run(
        self,
        instruction: client_types.Instruction,
    ) -> client_types.ExecutionResult:
        payload = instruction["payload"]
        prompt = payload.get("prompt")
        prompt_ref = payload.get("prompt_ref")
        spec_ref = payload.get("spec_ref")
        mode = payload.get("mode", "exec")
        args = payload.get("args", [])
        model = payload.get("model")
        foreground = payload.get("foreground", True)
        ref_root = instruction.get("ref_root")
        output_json = payload.get("output_json")

        cwd = resource_refs_module.resolve_cwd(
            instruction.get("cwd"),
            self._roots,
        )
        output_json_path = self._output_json_path(cwd, output_json)
        output_json_mode = self._output_json_mode(output_json)
        output_file_paths = self._output_file_paths(cwd, payload.get("output_files", []))
        target_dirs = self._target_paths(cwd, payload.get("target_dirs", []), "target_dirs", expected_type="dir")
        target_files = self._target_paths(cwd, payload.get("target_files", []), "target_files", expected_type="file")
        prompt_text, main_prompt_path, context_paths = self._prompt_text(
            str(cwd),
            prompt,
            prompt_ref,
            spec_ref,
            payload.get("context_refs", []),
            target_dirs,
            target_files,
            output_json_path,
            output_json_mode,
            output_file_paths,
            ref_root,
        )
        if mode != "exec":
            raise ValueError("codex instruction payload mode currently only supports 'exec'.")
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            raise ValueError("codex instruction payload args must be a list of strings.")
        default_model = None
        if model is None and not self._has_model_arg(args):
            default_model = self._default_model(cwd)
        codex_args = self._codex_args(args, model, default_model)

        if foreground and os.name == "nt":
            if output_json_path is not None:
                raise ValueError("codex instruction payload output_json cannot be used with foreground=true on Windows.")
            return self._run_foreground_windows(
                instruction,
                cwd,
                prompt_text,
                codex_args,
                mode,
                main_prompt_path,
                context_paths,
                target_dirs,
                target_files,
                output_json_path,
                output_json_mode,
                output_file_paths,
            )

        return self._run_direct(
            instruction,
            cwd,
            prompt_text,
            codex_args,
            mode,
            main_prompt_path,
            context_paths,
            target_dirs,
            target_files,
            output_json_path,
            output_json_mode,
            output_file_paths,
        )

    def _subprocess_timeout(
        self,
        instruction: client_types.Instruction,
        *,
        extra: int = 0,
    ) -> float | None:
        timeout_seconds = instruction.get("timeout_seconds")
        if timeout_seconds is None:
            return None
        return float(timeout_seconds + extra)

    def _run_direct(
        self,
        instruction: client_types.Instruction,
        cwd: pathlib.Path,
        prompt_text: str,
        args: list[str],
        mode: str,
        main_prompt_path: str | None,
        context_paths: list[dict[str, str]],
        target_dirs: list[str],
        target_files: list[str],
        output_json_path: pathlib.Path | None,
        output_json_mode: str,
        output_file_paths: list[pathlib.Path],
    ) -> client_types.ExecutionResult:
        command = [
            "codex",
            "exec",
            *args,
            "-",
        ]
        launch_command = process_execution_module.CommandResolver().resolve(command)
        track_dir = self._create_track_dir(cwd, instruction["id"])
        stdout_path = track_dir / "stdout.txt"
        stderr_path = track_dir / "stderr.txt"
        self._write_track_start(
            track_dir,
            instruction,
            cwd,
            launch_command,
            prompt_text,
            mode,
            main_prompt_path,
            context_paths,
            target_dirs,
            target_files,
            output_json_path,
            output_json_mode,
            output_file_paths,
        )

        with stdout_path.open("w", encoding="utf-8", errors="replace") as stdout_file:
            with stderr_path.open("w", encoding="utf-8", errors="replace") as stderr_file:
                try:
                    process = process_execution_module.popen_cli_command(
                        command,
                        cwd=cwd,
                        stdin=subprocess.PIPE,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        env=self._codex_env(),
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        **self._background_process_kwargs(),
                    )
                except (FileNotFoundError, PermissionError) as exc:
                    self._write_track_launch_error(track_dir, instruction, cwd, mode, exc)
                    raise RuntimeError(f"Codex CLI launch failed: {exc}") from exc
                try:
                    process.communicate(prompt_text, timeout=self._subprocess_timeout(instruction))
                    returncode = process.returncode if process.returncode is not None else process.wait()
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    self._write_track_finish(
                        track_dir,
                        instruction,
                        cwd,
                        mode,
                        -1,
                        timed_out=True,
                        runner_error_type="TimeoutExpired",
                        runner_error_message=f"Codex CLI timed out after {instruction.get('timeout_seconds')} seconds.",
                    )
                    raise
                except BaseException as exc:
                    self._write_track_finish(
                        track_dir,
                        instruction,
                        cwd,
                        mode,
                        -1,
                        timed_out=False,
                        runner_error_type=type(exc).__name__,
                        runner_error_message=str(exc),
                    )
                    raise

        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        self._write_track_finish(
            track_dir,
            instruction,
            cwd,
            mode,
            returncode,
            timed_out=False,
        )

        result = self._result_from_completed(
            instruction,
            cwd,
            mode,
            returncode,
            stdout,
            stderr,
            foreground=False,
            main_prompt_path=main_prompt_path,
            context_paths=context_paths,
            target_dirs=target_dirs,
            target_files=target_files,
        )
        if result["ok"]:
            try:
                if output_json_path is not None:
                    self._write_output_json(output_json_path, output_json_mode, stdout, stderr, result)
                self._validate_output_files(output_file_paths, result)
            except Exception as exc:
                self._write_track_finish(
                    track_dir,
                    instruction,
                    cwd,
                    mode,
                    1,
                    timed_out=False,
                    runner_error_type=type(exc).__name__,
                    runner_error_message=str(exc),
                )
                raise
        token_usage = result["metadata"].get("token_usage")
        if isinstance(token_usage, dict):
            self._write_track_token_usage(track_dir, token_usage)
        result["metadata"]["background"] = True
        self._attach_track_result(result, track_dir, prompt_text, stdout_path, stderr_path)
        return result

    def _codex_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env.setdefault("LC_ALL", "C.UTF-8")
        env.setdefault("LANG", "C.UTF-8")
        if os.name == "nt":
            env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
        return env

    def _background_process_kwargs(self) -> dict[str, Any]:
        flags = process_execution_module.background_no_window_flags()
        return {} if flags == 0 else {"creationflags": flags}

    def _attach_track_result(
        self,
        result: client_types.ExecutionResult,
        track_dir: pathlib.Path,
        prompt_text: str,
        stdout_path: pathlib.Path,
        stderr_path: pathlib.Path,
    ) -> None:
        result["metadata"]["track_dir"] = str(track_dir)
        result["metadata"]["prompt_transport"] = "stdin"
        result["metadata"]["handoff_prompt_path"] = str(track_dir / "handoff_prompt.txt")
        result["metadata"]["handoff_prompt_bytes"] = len(prompt_text.encode("utf-8"))
        result["metadata"]["track_files"] = {
            "prompt": str(track_dir / "prompt.txt"),
            "handoff_prompt": str(track_dir / "handoff_prompt.txt"),
            "command": str(track_dir / "command.json"),
            "stdout": str(stdout_path),
            "stderr": str(stderr_path),
            "metadata": str(track_dir / "metadata.json"),
        }
        result["artifacts"].append(
            {
                "type": "codex_track",
                "path": str(track_dir),
            }
        )

    def _create_track_dir(self, cwd: pathlib.Path, instruction_id: str) -> pathlib.Path:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", instruction_id).strip("._-")
        if not safe_id:
            safe_id = "codex"
        timestamp = time.strftime("%Y%m%dT%H%M%S")
        track_root = file_ops_module.ensure_dir(workspace_layout_module.codex_dir(cwd))
        for attempt in range(1000):
            suffix = f"{timestamp}-{attempt:03d}"
            path = track_root / f"{safe_id}-{suffix}"
            try:
                path.mkdir()
            except FileExistsError:
                continue
            return path
        raise RuntimeError(f"failed to create Codex track directory under {track_root}")

    def _write_track_start(
        self,
        track_dir: pathlib.Path,
        instruction: client_types.Instruction,
        cwd: pathlib.Path,
        command: list[str],
        prompt_text: str,
        mode: str,
        main_prompt_path: str | None,
        context_paths: list[dict[str, str]],
        target_dirs: list[str],
        target_files: list[str],
        output_json_path: pathlib.Path | None = None,
        output_json_mode: str = "managed",
        output_file_paths: list[pathlib.Path] | None = None,
        *,
        foreground: bool = False,
        background: bool = True,
    ) -> None:
        file_ops_module.write_text_atomic(track_dir / "prompt.txt", prompt_text)
        handoff_prompt_path = track_dir / "handoff_prompt.txt"
        file_ops_module.write_text_atomic(handoff_prompt_path, prompt_text)
        self._write_json(
            track_dir / "command.json",
            {
                "instruction_id": instruction["id"],
                "cwd": str(cwd),
                "command": command,
            },
        )
        self._write_json(
            track_dir / "metadata.json",
            {
                "instruction_id": instruction["id"],
                "cwd": str(cwd),
                "mode": mode,
                "foreground": foreground,
                "background": background,
                "main_prompt_path": main_prompt_path,
                "context_paths": context_paths,
                "target_dirs": target_dirs,
                "target_files": target_files,
                "output_json": (
                    {"path": str(output_json_path), "mode": output_json_mode}
                    if output_json_path is not None
                    else None
                ),
                "output_files": [str(path) for path in (output_file_paths or [])],
                "prompt_transport": "stdin",
                "handoff_prompt_path": str(handoff_prompt_path),
                "handoff_prompt_bytes": len(prompt_text.encode("utf-8")),
                "timeout": instruction.get("timeout_seconds"),
                "started_at_unix": time.time(),
                "exit_code": None,
                "timed_out": False,
            },
        )

    def _write_track_finish(
        self,
        track_dir: pathlib.Path,
        instruction: client_types.Instruction,
        cwd: pathlib.Path,
        mode: str,
        returncode: int,
        *,
        timed_out: bool,
        runner_error_type: str | None = None,
        runner_error_message: str | None = None,
        foreground: bool = False,
        background: bool = True,
    ) -> None:
        metadata_path = track_dir / "metadata.json"
        metadata: dict[str, Any] = {}
        if metadata_path.exists():
            try:
                loaded = file_ops_module.read_json(metadata_path)
                if isinstance(loaded, dict):
                    metadata = loaded
            except file_ops_module.FileOperationError:
                metadata = {}
        metadata.update(
            {
                "instruction_id": instruction["id"],
                "cwd": str(cwd),
                "mode": mode,
                "foreground": foreground,
                "background": background,
                "finished_at_unix": time.time(),
                "exit_code": returncode,
                "timed_out": timed_out,
            }
        )
        if runner_error_type is not None:
            metadata["runner_error_type"] = runner_error_type
        if runner_error_message is not None:
            metadata["runner_error_message"] = runner_error_message
            metadata["error_message"] = runner_error_message
        self._write_json(metadata_path, metadata)

    def _write_track_token_usage(self, track_dir: pathlib.Path, token_usage: dict[str, int]) -> None:
        metadata_path = track_dir / "metadata.json"
        metadata: dict[str, Any] = {}
        if metadata_path.exists():
            try:
                loaded = file_ops_module.read_json(metadata_path)
                if isinstance(loaded, dict):
                    metadata = loaded
            except file_ops_module.FileOperationError:
                metadata = {}
        metadata["token_usage"] = token_usage
        self._write_json(metadata_path, metadata)

    def _write_track_launch_error(
        self,
        track_dir: pathlib.Path,
        instruction: client_types.Instruction,
        cwd: pathlib.Path,
        mode: str,
        exc: Exception,
    ) -> None:
        metadata_path = track_dir / "metadata.json"
        metadata: dict[str, Any] = {}
        if metadata_path.exists():
            try:
                loaded = file_ops_module.read_json(metadata_path)
                if isinstance(loaded, dict):
                    metadata = loaded
            except file_ops_module.FileOperationError:
                metadata = {}
        metadata.update(
            {
                "instruction_id": instruction["id"],
                "cwd": str(cwd),
                "mode": mode,
                "foreground": False,
                "background": True,
                "finished_at_unix": time.time(),
                "runner_error_type": "launch_failed",
                "error_message": str(exc),
                "exit_code": None,
                "timed_out": False,
            }
        )
        self._write_json(metadata_path, metadata)

    def _write_json(self, path: pathlib.Path, data: dict[str, Any]) -> None:
        file_ops_module.write_json_atomic(path, data)

    def _output_json_path(self, cwd: pathlib.Path, output_json: Any) -> pathlib.Path | None:
        if output_json is None:
            return None
        if not isinstance(output_json, dict):
            raise ValueError("codex instruction payload output_json must be an object when provided.")
        raw_path = output_json.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("codex instruction payload output_json.path must be a non-empty string.")
        if pathlib.Path(raw_path).suffix.lower() != ".json":
            raise ValueError("codex instruction payload output_json.path must reference a .json file.")
        return file_ops_module.resolve_under_root(cwd, raw_path)

    def _output_json_mode(self, output_json: Any) -> str:
        if output_json is None:
            return "managed"
        if not isinstance(output_json, dict):
            raise ValueError("codex instruction payload output_json must be an object when provided.")
        mode = output_json.get("mode", "managed")
        if mode not in {"managed", "file"}:
            raise ValueError("codex instruction payload output_json.mode must be 'managed' or 'file'.")
        return mode

    def _output_file_paths(self, cwd: pathlib.Path, output_files: Any) -> list[pathlib.Path]:
        if output_files is None:
            return []
        if not isinstance(output_files, list):
            raise ValueError("codex instruction payload output_files must be a list.")
        paths: list[pathlib.Path] = []
        seen: set[pathlib.Path] = set()
        for index, item in enumerate(output_files):
            label = f"output_files[{index}]"
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"codex instruction payload {label} must be a non-empty string.")
            if pathlib.Path(item).suffix.lower() == ".json":
                raise ValueError(f"codex instruction payload {label} references a .json file; use output_json.")
            path = file_ops_module.resolve_under_root(cwd, item)
            if path in seen:
                raise ValueError(f"codex instruction payload {label} duplicates output file: {item}")
            seen.add(path)
            paths.append(path)
        return paths

    def _write_output_json(
        self,
        output_json_path: pathlib.Path,
        output_json_mode: str,
        stdout: str,
        stderr: str,
        result: client_types.ExecutionResult,
    ) -> None:
        if output_json_mode == "file":
            data = self._read_file_output_json(output_json_path)
        else:
            data = self._extract_json_object(stdout, stderr)
        rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
        report = self._mojibake_report(rendered)
        metadata = result.setdefault("metadata", {})
        if report["detected"]:
            raise ValueError(f"{output_json_mode} output JSON appears mojibake-corrupted: {report['reason']}")
        if output_json_mode == "managed":
            file_ops_module.write_json_atomic(output_json_path, data)
        output_metadata: dict[str, Any] = {
            "path": str(output_json_path),
            "mode": output_json_mode,
            "validated": True,
            "mojibake_detected": False,
        }
        if output_json_mode == "managed":
            output_metadata["data"] = data
        else:
            output_metadata["size_bytes"] = output_json_path.stat().st_size
        metadata["output_json"] = output_metadata
        result["artifacts"].append({"type": f"{output_json_mode}_json_output", "path": str(output_json_path)})

    def _validate_output_files(
        self,
        output_file_paths: list[pathlib.Path],
        result: client_types.ExecutionResult,
    ) -> None:
        if not output_file_paths:
            return
        metadata = result.setdefault("metadata", {})
        output_metadata: list[dict[str, Any]] = []
        for path in output_file_paths:
            if not path.is_file():
                raise ValueError(f"file output was requested, but Codex did not create the file: {path}")
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(f"file output must be UTF-8 encoded: {path}") from exc
            report = self._mojibake_report(text)
            if report["detected"]:
                raise ValueError(f"file output appears mojibake-corrupted: {path}: {report['reason']}")
            item = {
                "path": str(path),
                "validated": True,
                "size_bytes": path.stat().st_size,
                "mojibake_detected": False,
            }
            output_metadata.append(item)
            result["artifacts"].append({"type": "file_output", "path": str(path)})
        metadata["output_files"] = output_metadata

    def _read_file_output_json(self, output_json_path: pathlib.Path) -> dict[str, Any]:
        if not output_json_path.is_file():
            raise ValueError(f"file output JSON was requested, but Codex did not create the file: {output_json_path}")
        try:
            text = output_json_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("file output JSON must be UTF-8 encoded.") from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"file output JSON is invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("file output JSON must be a JSON object.")
        return data

    def _extract_json_object(self, stdout: str, stderr: str) -> dict[str, Any]:
        for text in (stdout, stderr):
            data = self._json_object_from_json_events(text)
            if data is not None:
                return data
        if any(self._looks_like_json_events(text) for text in (stdout, stderr)):
            raise ValueError("managed output JSON was requested, but Codex JSON events did not contain a JSON object.")
        for text in (stdout, stderr):
            data = self._first_json_value(text)
            if data is not None:
                if not isinstance(data, dict):
                    raise ValueError("managed output JSON must be a JSON object.")
                return data
        raise ValueError("managed output JSON was requested, but Codex output did not contain a JSON object.")

    def _json_object_from_json_events(self, text: str) -> dict[str, Any] | None:
        for event in reversed(self._json_event_objects(text)):
            for candidate in self._event_text_values(event):
                data = self._first_json_value(candidate)
                if data is None:
                    continue
                if not isinstance(data, dict):
                    raise ValueError("managed output JSON must be a JSON object.")
                return data
        return None

    def _looks_like_json_events(self, text: str) -> bool:
        return any(isinstance(event.get("type"), str) for event in self._json_event_objects(text))

    def _json_event_objects(self, text: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                events.append(data)
        return events

    def _event_text_values(self, value: Any) -> list[str]:
        values: list[str] = []
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, dict):
            for key in ("message", "text", "content", "output", "final", "last_message", "item", "delta"):
                if key in value:
                    values.extend(self._event_text_values(value[key]))
        elif isinstance(value, list):
            for item in value:
                values.extend(self._event_text_values(item))
        return values

    def _first_json_value(self, text: str) -> Any | None:
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "{[":
                continue
            try:
                data, _end = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            return data
        return None

    def _mojibake_report(self, text: str) -> dict[str, Any]:
        if not text:
            return {"detected": False, "reason": ""}
        markers = ("楠", "鐢", "閺", "鏂", "绛", "闃", "銆", "锛", "濂", "妫")
        marker_count = sum(text.count(marker) for marker in markers)
        question_count = text.count("?")
        cjk_count = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
        if marker_count >= 20:
            return {"detected": True, "reason": f"mojibake marker count is {marker_count}"}
        if cjk_count >= 20 and question_count / max(len(text), 1) > 0.05:
            return {"detected": True, "reason": f"question mark ratio is {question_count / max(len(text), 1):.3f}"}
        return {"detected": False, "reason": ""}

    def _run_foreground_windows(
        self,
        instruction: client_types.Instruction,
        cwd: pathlib.Path,
        prompt_text: str,
        args: list[str],
        mode: str,
        main_prompt_path: str | None,
        context_paths: list[dict[str, str]],
        target_dirs: list[str],
        target_files: list[str],
        output_json_path: pathlib.Path | None,
        output_json_mode: str,
        output_file_paths: list[pathlib.Path],
    ) -> client_types.ExecutionResult:
        command = [
            "codex",
            "exec",
            *args,
            "-",
        ]
        launch_command = process_execution_module.CommandResolver().resolve(command)
        track_dir = self._create_track_dir(cwd, instruction["id"])
        stdout_path = track_dir / "stdout.txt"
        stderr_path = track_dir / "stderr.txt"
        self._write_track_start(
            track_dir,
            instruction,
            cwd,
            launch_command,
            prompt_text,
            mode,
            main_prompt_path,
            context_paths,
            target_dirs,
            target_files,
            output_json_path,
            output_json_mode,
            output_file_paths,
            foreground=True,
            background=False,
        )
        with tempfile.TemporaryDirectory(prefix="lgwf-codex-") as temp_dir:
            temp_root = pathlib.Path(temp_dir)
            prompt_path = temp_root / "prompt.txt"
            args_path = temp_root / "args.json"
            runner_path = temp_root / "run_codex.py"
            exit_code_path = temp_root / "exit_code.txt"

            file_ops_module.write_text_atomic(prompt_path, prompt_text)
            file_ops_module.write_json_atomic(args_path, args, indent=None)
            file_ops_module.write_text_atomic(
                runner_path,
                self._foreground_runner_source(
                    cwd,
                    prompt_path,
                    args_path,
                    exit_code_path,
                ),
            )

            title = f"LGWF Codex {instruction['id']}"
            python_env = python_execution_module.discover_python()
            completed = process_execution_module.run_command(
                [
                    "cmd.exe",
                    "/c",
                    "start",
                    title,
                    "/wait",
                    *python_env.script_command(runner_path),
                ],
                cwd=temp_root,
                env=python_env.env(),
                timeout_seconds=self._subprocess_timeout(instruction, extra=15),
            )

            returncode = self._foreground_returncode(exit_code_path, completed.returncode)

        file_ops_module.write_text_atomic(stdout_path, "")
        file_ops_module.write_text_atomic(stderr_path, completed.stderr)
        self._write_track_finish(
            track_dir,
            instruction,
            cwd,
            mode,
            returncode,
            timed_out=completed.timed_out,
            runner_error_type="TimeoutExpired" if completed.timed_out else None,
            runner_error_message=(
                f"Codex CLI timed out after {instruction.get('timeout_seconds')} seconds."
                if completed.timed_out
                else None
            ),
            foreground=True,
            background=False,
        )

        result = self._result_from_completed(
            instruction,
            cwd,
            mode,
            returncode,
            "",
            completed.stderr,
            foreground=True,
            interactive=True,
            main_prompt_path=main_prompt_path,
            context_paths=context_paths,
            target_dirs=target_dirs,
            target_files=target_files,
        )
        if result["ok"]:
            try:
                self._validate_output_files(output_file_paths, result)
            except Exception as exc:
                self._write_track_finish(
                    track_dir,
                    instruction,
                    cwd,
                    mode,
                    1,
                    timed_out=False,
                    runner_error_type=type(exc).__name__,
                    runner_error_message=str(exc),
                    foreground=True,
                    background=False,
                )
                raise
        result["metadata"]["background"] = False
        self._attach_track_result(result, track_dir, prompt_text, stdout_path, stderr_path)
        return result

    def _result_from_completed(
        self,
        instruction: client_types.Instruction,
        cwd: pathlib.Path,
        mode: str,
        returncode: int,
        stdout: str,
        stderr: str,
        foreground: bool,
        interactive: bool = False,
        main_prompt_path: str | None = None,
        context_paths: list[dict[str, str]] | None = None,
        target_dirs: list[str] | None = None,
        target_files: list[str] | None = None,
    ) -> client_types.ExecutionResult:
        metadata: dict[str, Any] = {
            "cwd": str(cwd),
            "mode": mode,
            "foreground": foreground,
            "interactive": interactive,
            "timeout": instruction.get("timeout_seconds"),
        }
        if main_prompt_path is not None:
            metadata["main_prompt_path"] = main_prompt_path
        if context_paths is not None:
            metadata["context_paths"] = context_paths
        if target_dirs is not None:
            metadata["target_dirs"] = target_dirs
        if target_files is not None:
            metadata["target_files"] = target_files
        token_usage = self._parse_token_usage(stdout, stderr)
        if token_usage is not None:
            metadata["token_usage"] = token_usage

        return {
            "instruction_id": instruction["id"],
            "ok": returncode == 0,
            "exit_code": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "artifacts": [],
            "changed_files": [],
            "metadata": metadata,
        }

    def _foreground_runner_source(
        self,
        cwd: pathlib.Path,
        prompt_path: pathlib.Path,
        args_path: pathlib.Path,
        exit_code_path: pathlib.Path,
    ) -> str:
        return f'''import json
import os
import pathlib
import subprocess
import time

import lgwf_client.process_execution as process_execution

cwd = pathlib.Path({str(cwd)!r})
prompt = pathlib.Path({str(prompt_path)!r}).read_text(encoding="utf-8")
args = json.loads(pathlib.Path({str(args_path)!r}).read_text(encoding="utf-8"))
exit_code_path = pathlib.Path({str(exit_code_path)!r})

command = process_execution.CommandResolver().resolve(["codex", *args, "-"])
completed = subprocess.run(
    command,
    cwd=cwd,
    env={{
        **os.environ,
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONLEGACYWINDOWSSTDIO": "0",
    }},
    input=prompt,
    text=True,
    encoding="utf-8",
    errors="replace",
)
exit_code_path.write_text(str(completed.returncode), encoding="utf-8")
time.sleep(5)
raise SystemExit(completed.returncode)
'''

    def _foreground_returncode(self, exit_code_path: pathlib.Path, fallback: int) -> int:
        if not exit_code_path.exists():
            return fallback
        try:
            return int(exit_code_path.read_text(encoding="utf-8").strip())
        except ValueError:
            return fallback

    def _parse_token_usage(self, stdout: str, stderr: str) -> dict[str, int] | None:
        text = "\n".join(part for part in (stdout, stderr) if part)
        if not text:
            return None

        usage = self._parse_json_usage(text)
        if usage is None:
            usage = self._parse_text_usage(text)
        if usage is None:
            return None

        normalized = self._normalize_token_usage(usage)
        if not any(normalized.values()):
            return None
        return normalized

    def _parse_json_usage(self, text: str) -> dict[str, Any] | None:
        for line in text.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            usage = self._find_usage_object(data)
            if usage is not None:
                return usage
        return None

    def _find_usage_object(self, value: Any) -> dict[str, Any] | None:
        if isinstance(value, dict):
            for key in ("token_usage", "usage"):
                candidate = value.get(key)
                if isinstance(candidate, dict):
                    return candidate
            if any(key in value for key in ("input_tokens", "output_tokens", "total_tokens")):
                return value
            for item in value.values():
                candidate = self._find_usage_object(item)
                if candidate is not None:
                    return candidate
        elif isinstance(value, list):
            for item in value:
                candidate = self._find_usage_object(item)
                if candidate is not None:
                    return candidate
        return None

    def _parse_text_usage(self, text: str) -> dict[str, int] | None:
        usage: dict[str, int] = {}
        patterns = {
            "input_tokens": [
                r"\binput(?:\s+tokens)?\s*[:=]\s*([0-9][0-9,]*)",
                r"\bprompt(?:\s+tokens)?\s*[:=]\s*([0-9][0-9,]*)",
            ],
            "output_tokens": [
                r"\boutput(?:\s+tokens)?\s*[:=]\s*([0-9][0-9,]*)",
                r"\bcompletion(?:\s+tokens)?\s*[:=]\s*([0-9][0-9,]*)",
            ],
            "total_tokens": [
                r"\btotal(?:\s+tokens)?\s*[:=]\s*([0-9][0-9,]*)",
            ],
            "cached_input_tokens": [
                r"\bcached(?:\s+input)?(?:\s+tokens)?\s*[:=]\s*([0-9][0-9,]*)",
                r"\+\s*([0-9][0-9,]*)\s+cached",
            ],
            "reasoning_output_tokens": [
                r"\breasoning(?:\s+output)?(?:\s+tokens)?\s*[:=]\s*([0-9][0-9,]*)",
                r"\(reasoning\s+([0-9][0-9,]*)\)",
            ],
        }
        for key, key_patterns in patterns.items():
            for pattern in key_patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE)
                if match:
                    usage[key] = self._parse_int(match.group(1))
                    break
        return usage or None

    def _normalize_token_usage(self, usage: dict[str, Any]) -> dict[str, int]:
        aliases = {
            "input_tokens": ("input_tokens", "prompt_tokens", "input", "prompt"),
            "output_tokens": ("output_tokens", "completion_tokens", "output", "completion"),
            "total_tokens": ("total_tokens", "total"),
            "cached_input_tokens": ("cached_input_tokens", "cached_tokens", "cached_input", "cached"),
            "reasoning_output_tokens": (
                "reasoning_output_tokens",
                "reasoning_tokens",
                "output_reasoning_tokens",
                "reasoning",
            ),
        }
        normalized: dict[str, int] = {}
        for target_key, source_keys in aliases.items():
            normalized[target_key] = 0
            for source_key in source_keys:
                if source_key in usage:
                    normalized[target_key] = self._parse_int(usage[source_key])
                    break
        if normalized["total_tokens"] == 0:
            normalized["total_tokens"] = normalized["input_tokens"] + normalized["output_tokens"]
        return normalized

    def _parse_int(self, value: Any) -> int:
        if isinstance(value, bool):
            return 0
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, float):
            return max(int(value), 0)
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            if cleaned.isdigit():
                return int(cleaned)
        return 0

    def _codex_args(self, args: list[str], model: Any, default_model: str | None = None) -> list[str]:
        has_model_arg = self._has_model_arg(args)
        if model is not None and (not isinstance(model, str) or not model.strip()):
            raise ValueError("codex instruction payload model must be a non-empty string when provided.")
        if model is not None and has_model_arg:
            raise ValueError("codex instruction payload model must not be set in both model and args.")
        transport_args = self._transport_args(args)
        json_args = self._json_args(args)
        exec_args = self._default_exec_args(args)
        if model is not None:
            return [*transport_args, *json_args, *exec_args, *args, "--model", model]
        if has_model_arg:
            return [*transport_args, *json_args, *exec_args, *args]
        return [*transport_args, *json_args, *exec_args, *args, "--model", default_model or DEFAULT_CODEX_MODEL]

    def _default_model(self, cwd: pathlib.Path) -> str:
        workspace_root = self._roots.workspace_root
        root = pathlib.Path(workspace_root).resolve() if workspace_root is not None else cwd
        return str(codex_config_module.get_codex_model(root)["model"])

    def _has_model_arg(self, args: list[str]) -> bool:
        return any(item == "-m" or item == "--model" or item.startswith("--model=") for item in args)

    def _transport_args(self, args: list[str]) -> list[str]:
        if "responses_websockets" in args or "responses_websockets_v2" in args:
            return []
        return DEFAULT_CODEX_TRANSPORT_ARGS

    def _json_args(self, args: list[str]) -> list[str]:
        if "--json" in args:
            return []
        return DEFAULT_CODEX_JSON_ARGS

    def _default_exec_args(self, args: list[str]) -> list[str]:
        if "--skip-git-repo-check" in args:
            return []
        return DEFAULT_CODEX_EXEC_ARGS

    def _prompt_text(
        self,
        cwd: str,
        prompt: Any,
        prompt_ref: Any,
        spec_ref: Any = None,
        context_refs: Any = None,
        target_dirs: list[str] | None = None,
        target_files: list[str] | None = None,
        output_json_path: pathlib.Path | None = None,
        output_json_mode: str = "managed",
        output_file_paths: list[pathlib.Path] | None = None,
        ref_root: Any = None,
    ) -> tuple[str, str | None, list[dict[str, str]]]:
        has_prompt = isinstance(prompt, str) and bool(prompt.strip())
        has_prompt_ref = prompt_ref is not None

        if has_prompt == has_prompt_ref:
            raise ValueError("codex instruction payload requires exactly one of prompt or prompt_ref.")

        spec_path: pathlib.Path | None = None
        if spec_ref is not None:
            spec_path = resource_refs_module.resolve_resource_path(
                cwd,
                spec_ref,
                "spec_ref",
                self._roots,
                ref_root,
            )
            if not spec_path.is_file():
                raise ValueError(f"codex instruction spec_ref does not exist or is not a file: {spec_path}")

        if has_prompt:
            output_text = (
                self._output_json_instruction(output_json_path, output_json_mode)
                + self._output_files_instruction(output_file_paths or [])
            )
            if spec_path is not None:
                return (
                    self._render_inline_spec_prompt(prompt, spec_path) + output_text,
                    None,
                    [],
                )
            return prompt + output_text, None, []

        prompt_path = resource_refs_module.resolve_resource_path(cwd, prompt_ref, "prompt_ref", self._roots, ref_root)
        if not prompt_path.is_file():
            raise ValueError(f"codex instruction prompt_ref does not exist or is not a file: {prompt_path}")
        context_paths = self._context_paths(cwd, context_refs, ref_root)
        return (
            self._render_handoff_prompt(
                cwd,
                prompt_path,
                spec_path,
                context_paths,
                target_dirs or [],
                target_files or [],
                output_json_path,
                output_json_mode,
                output_file_paths or [],
            ),
            str(prompt_path),
            context_paths,
        )

    def _render_inline_spec_prompt(self, prompt: str, spec_path: pathlib.Path) -> str:
        return (
            "# LGWF Codex Handoff\n\n"
            f"Governing spec file:\n{spec_path}\n\n"
            "The governing spec is authoritative. If it conflicts with the main prompt, "
            "follow the governing spec.\n\n"
            f"Main prompt:\n{prompt}\n"
        )

    def _context_paths(
        self,
        cwd: str,
        context_refs: Any,
        ref_root: Any = None,
    ) -> list[dict[str, str]]:
        if context_refs is None:
            return []
        if not isinstance(context_refs, list):
            raise ValueError("codex instruction payload context_refs must be a list.")

        resolved: list[dict[str, str]] = []
        for index, item in enumerate(context_refs):
            label = f"context_refs[{index}]"
            if not isinstance(item, dict):
                raise ValueError(f"codex instruction payload {label} must be an object.")
            ref_type = item.get("type")
            if ref_type not in {"file", "dir"}:
                raise ValueError(f"codex instruction payload {label}.type must be 'file' or 'dir'.")
            path = resource_refs_module.resolve_resource_path(cwd, item, label, self._roots, ref_root)
            if ref_type == "file" and not path.is_file():
                raise ValueError(f"codex instruction payload {label} must be a file: {path}")
            if ref_type == "dir" and not path.is_dir():
                raise ValueError(f"codex instruction payload {label} must be a directory: {path}")
            resolved.append(
                {
                    "type": ref_type,
                    "path": str(path),
                }
            )
        return resolved

    def _render_handoff_prompt(
        self,
        cwd: str,
        prompt_path: pathlib.Path,
        spec_path: pathlib.Path | None,
        context_paths: list[dict[str, str]],
        target_dirs: list[str],
        target_files: list[str],
        output_json_path: pathlib.Path | None = None,
        output_json_mode: str = "managed",
        output_file_paths: list[pathlib.Path] | None = None,
    ) -> str:
        template = HANDOFF_TEMPLATE_PATH.read_text(encoding="utf-8")
        context_text = "\n".join(
            f"- {item['type']}: {item['path']}"
            for item in context_paths
        )
        if not context_text:
            context_text = "- none"
        target_dirs_text = "\n".join(f"- dir: {path}" for path in target_dirs)
        if not target_dirs_text:
            target_dirs_text = "- none"
        target_files_text = "\n".join(f"- file: {path}" for path in target_files)
        if not target_files_text:
            target_files_text = "- none"
        spec_text = str(spec_path) if spec_path is not None else "- none"
        managed_json_context = self._render_managed_json_context(context_paths)

        return (
            template
            .replace("{{main_prompt_path}}", str(prompt_path))
            .replace("{{spec_path}}", spec_text)
            .replace("{{workspace_root}}", str(pathlib.Path(cwd).resolve()))
            .replace("{{context_paths}}", context_text)
            .replace("{{target_dirs}}", target_dirs_text)
            .replace("{{target_files}}", target_files_text)
            + managed_json_context
            + self._output_json_instruction(output_json_path, output_json_mode)
            + self._output_files_instruction(output_file_paths or [])
        )

    def _render_managed_json_context(self, context_paths: list[dict[str, str]]) -> str:
        json_files = [
            pathlib.Path(item["path"])
            for item in context_paths
            if item.get("type") == "file" and pathlib.Path(item.get("path", "")).suffix.lower() == ".json"
        ]
        if not json_files:
            return ""

        sections = [
            "\n\nRuntime-provided JSON context:\n",
            "The following JSON files were read by LGWF runtime using UTF-8 and parsed before Codex was started. "
            "Treat this section as authoritative. Do not read these JSON files with shell, PowerShell, or ad-hoc scripts.\n",
        ]
        for path in json_files:
            text = path.read_text(encoding="utf-8-sig")
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON context is invalid: {path}: {exc.msg}") from exc
            report = self._mojibake_report(text)
            if report["detected"]:
                raise ValueError(f"JSON context appears mojibake-corrupted: {path}: {report['reason']}")
            rendered = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
            sections.append(f"\n[json_context:{path.name}]\npath: {path}\nparsed: true\nmojibake_detected: false\ncontent:\n")
            sections.append("```json\n")
            sections.append(rendered)
            sections.append("\n```\n")
        return "".join(sections)

    def _output_json_instruction(self, output_json_path: pathlib.Path | None, output_json_mode: str = "managed") -> str:
        if output_json_path is None:
            return ""
        if output_json_mode == "file":
            return (
                "\n\nCodex-written JSON output:\n"
                f"- Output path: {output_json_path}\n"
                "- Write, edit, or create this output JSON file yourself before finishing.\n"
                "- The file must be UTF-8 encoded JSON with exactly one top-level object.\n"
                "- Your final response can be concise; LGWF runtime will validate the file after Codex exits.\n"
            )
        return (
            "\n\nRuntime-managed JSON output:\n"
            f"- Output path: {output_json_path}\n"
            "- Return exactly one JSON object in your final response.\n"
            "- Do not write, edit, or create the output JSON file yourself. LGWF runtime will parse your JSON object, "
            "validate it, and write the file using UTF-8 atomic IO.\n"
        )

    def _output_files_instruction(self, output_file_paths: list[pathlib.Path]) -> str:
        if not output_file_paths:
            return ""
        lines = [
            "\n\nCodex-written file outputs:\n",
            "- Write, edit, or create every listed output file before finishing.\n",
            "- Files must be UTF-8 encoded and must not be JSON artifacts; use OUTPUT_JSON for JSON.\n",
            "- LGWF runtime will verify each file exists and is readable after Codex exits.\n",
        ]
        for path in output_file_paths:
            lines.append(f"- Output path: {path}\n")
        return "".join(lines)

    def _target_paths(
        self,
        cwd: pathlib.Path,
        value: Any,
        label: str,
        *,
        expected_type: str,
    ) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"codex instruction payload {label} must be a list.")
        resolved: list[str] = []
        for index, item in enumerate(value):
            item_label = f"{label}[{index}]"
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"codex instruction payload {item_label} must be a non-empty string.")
            path = pathlib.Path(item).expanduser()
            if not path.is_absolute():
                path = cwd / path
            path = path.resolve()
            if expected_type == "dir" and not path.is_dir():
                raise ValueError(f"codex instruction payload {item_label} must be a directory: {path}")
            if expected_type == "file" and not path.is_file():
                raise ValueError(f"codex instruction payload {item_label} must be a file: {path}")
            resolved.append(str(path))
        return resolved

