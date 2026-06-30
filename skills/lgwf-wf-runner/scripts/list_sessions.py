from __future__ import annotations

import argparse
from pathlib import Path

from runner_common import (
    add_common_facade_arg,
    add_common_runner_arg,
    emit_json,
    read_json,
    resolve_facade_root,
    resolve_runner_root,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="List isolated LGWF workflow sessions.")
    add_common_facade_arg(parser)
    add_common_runner_arg(parser)
    parser.add_argument("--workflow-id")
    args = parser.parse_args()

    try:
        facade_root = resolve_facade_root(args.facade_root)
        runner_root = resolve_runner_root(args.runner_root)
        sessions = []
        for manifest_path in runner_root.glob("ws/sessions/*/*/.lgwf/main_agent/facade_session.json"):
            manifest = read_json(manifest_path)
            if args.workflow_id and manifest.get("workflow_id") != args.workflow_id:
                continue
            sessions.append(
                {
                    "workflow_id": manifest.get("workflow_id", ""),
                    "target_slug": manifest.get("target_slug", ""),
                    "facade_session_id": manifest.get("facade_session_id", ""),
                    "runtime_session_id": manifest.get("runtime_session_id", ""),
                    "pid": manifest.get("pid"),
                    "resolved_work_dir": manifest.get("resolved_work_dir", ""),
                    "manifest_path": str(Path(manifest_path).resolve()),
                }
            )
        sessions.sort(key=lambda item: item["facade_session_id"], reverse=True)
        emit_json({"ok": True, "facade_root": str(facade_root), "runner_root": str(runner_root), "sessions": sessions})
    except Exception as exc:
        emit_json({"ok": False, "error": str(exc)}, exit_code=1)


if __name__ == "__main__":
    main()
