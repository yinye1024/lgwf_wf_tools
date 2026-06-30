from __future__ import annotations

import argparse

from runner_common import (
    add_common_facade_arg,
    add_common_runner_arg,
    emit_json,
    resolve_facade_root,
    resolve_runner_root,
    resolve_work_dir,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve an isolated LGWF workflow work dir.")
    add_common_facade_arg(parser)
    add_common_runner_arg(parser)
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--target-slug")
    parser.add_argument("--facade-session-id")
    parser.add_argument("--create", action="store_true", help="创建 resolved work dir")
    args = parser.parse_args()

    try:
        facade_root = resolve_facade_root(args.facade_root)
        runner_root = resolve_runner_root(args.runner_root)
        result = resolve_work_dir(
            facade_root=facade_root,
            runner_root=runner_root,
            workflow_id=args.workflow_id,
            target_slug=args.target_slug,
            facade_session_id=args.facade_session_id,
            create=args.create,
        )
        emit_json({"ok": True, **result})
    except Exception as exc:
        emit_json({"ok": False, "error": str(exc)}, exit_code=1)


if __name__ == "__main__":
    main()
