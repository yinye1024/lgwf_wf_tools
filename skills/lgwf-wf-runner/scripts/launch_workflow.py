from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from runner_common import (
    add_common_facade_arg,
    add_common_runner_arg,
    emit_json,
    lgwf_py,
    parse_json_stdout,
    resolve_facade_root,
    resolve_runner_root,
    resolve_work_dir,
    run_command,
    write_json,
)


def read_input_json(args: argparse.Namespace) -> str:
    if args.input_json and args.input_json_file:
        raise ValueError("只允许提供 --input-json 或 --input-json-file 其中一个")
    if args.input_json_file:
        return Path(args.input_json_file).read_text(encoding="utf-8-sig")
    return args.input_json or "{}"


def build_input_args(args: argparse.Namespace, input_json: str) -> list[str]:
    if args.input_json_file:
        return ["--input-json-file", str(Path(args.input_json_file))]
    return ["--input-json", input_json]


def write_manifest(resolved: dict[str, Any], launch_result: dict[str, Any], input_json: str) -> dict[str, Any]:
    work_dir = Path(resolved["resolved_work_dir"])
    manifest = {
        "workflow_id": resolved["workflow_id"],
        "target_slug": resolved.get("target_slug", ""),
        "facade_session_id": resolved["facade_session_id"],
        "runtime_session_id": launch_result.get("session_id", ""),
        "pid": launch_result.get("pid"),
        "facade_root": resolved["facade_root"],
        "workflow_lgwf": resolved["workflow_lgwf"],
        "base_work_dir": resolved["base_work_dir"],
        "resolved_work_dir": resolved["resolved_work_dir"],
        "input_json": json.loads(input_json),
    }
    manifest_path = work_dir / ".lgwf" / "main_agent" / "facade_session.json"
    write_json(manifest_path, manifest)
    manifest["manifest_path"] = str(manifest_path)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch an LGWF workflow in an isolated work dir.")
    add_common_facade_arg(parser)
    add_common_runner_arg(parser)
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--target-slug")
    parser.add_argument("--facade-session-id")
    parser.add_argument("--input-json")
    parser.add_argument("--input-json-file")
    parser.add_argument("--timeout-seconds", type=int, default=60)
    args = parser.parse_args()

    try:
        facade_root = resolve_facade_root(args.facade_root)
        runner_root = resolve_runner_root(args.runner_root)
        input_json = read_input_json(args)
        json.loads(input_json)
        resolved = resolve_work_dir(
            facade_root=facade_root,
            runner_root=runner_root,
            workflow_id=args.workflow_id,
            target_slug=args.target_slug,
            facade_session_id=args.facade_session_id,
            create=True,
        )

        command = [
            "python",
            str(lgwf_py(facade_root)),
            "run",
            "--workflow-lgwf",
            resolved["workflow_lgwf"],
            "--work-dir",
            resolved["resolved_work_dir"],
            *build_input_args(args, input_json),
            "--background",
        ]
        proc = run_command(command, cwd=facade_root, timeout=args.timeout_seconds)
        if proc.returncode != 0:
            emit_json(
                {
                    "ok": False,
                    "resolved": resolved,
                    "command": command,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                },
                exit_code=proc.returncode,
            )
        launch_result = parse_json_stdout(proc)
        manifest = write_manifest(resolved, launch_result, input_json)
        emit_json({"ok": True, "resolved": resolved, "launch_result": launch_result, "manifest": manifest})
    except Exception as exc:
        emit_json({"ok": False, "error": str(exc)}, exit_code=1)


if __name__ == "__main__":
    main()
