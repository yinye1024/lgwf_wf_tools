from __future__ import annotations

import argparse
from pathlib import Path

from runner_common import (
    add_common_facade_arg,
    add_common_runner_arg,
    emit_json,
    lgwf_py,
    parse_json_stdout,
    read_json,
    resolve_facade_root,
    resolve_runner_root,
    run_command,
)


def find_manifest(runner_root: Path, facade_session_id: str) -> Path:
    pattern = f"ws/sessions/*/{facade_session_id}/.lgwf/main_agent/facade_session.json"
    matches = list(runner_root.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"session manifest not found: {facade_session_id}")
    if len(matches) > 1:
        raise RuntimeError(f"multiple session manifests found for {facade_session_id}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Query an isolated LGWF workflow session status.")
    add_common_facade_arg(parser)
    add_common_runner_arg(parser)
    parser.add_argument("--facade-session-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    args = parser.parse_args()

    try:
        facade_root = resolve_facade_root(args.facade_root)
        runner_root = resolve_runner_root(args.runner_root)
        manifest_path = find_manifest(runner_root, args.facade_session_id)
        manifest = read_json(manifest_path)
        command = [
            "python",
            str(lgwf_py(facade_root)),
            "status",
            "--work-dir",
            manifest["resolved_work_dir"],
        ]
        if manifest.get("runtime_session_id"):
            command.extend(["--session-id", str(manifest["runtime_session_id"])])
        elif manifest.get("pid"):
            command.extend(["--pid", str(manifest["pid"])])
        proc = run_command(command, cwd=facade_root, timeout=args.timeout_seconds)
        if proc.returncode != 0:
            emit_json(
                {
                    "ok": False,
                    "manifest": manifest,
                    "command": command,
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                },
                exit_code=proc.returncode,
            )
        emit_json({"ok": True, "manifest": manifest, "status": parse_json_stdout(proc)})
    except Exception as exc:
        emit_json({"ok": False, "error": str(exc)}, exit_code=1)


if __name__ == "__main__":
    main()
