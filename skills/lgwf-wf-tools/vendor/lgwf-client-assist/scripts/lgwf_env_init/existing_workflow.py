import argparse
import json
import pathlib
import shutil
from typing import TextIO

from . import process_status as process_status_module
from . import work_dir_guard as work_dir_guard_module
from .bootstrap import RuntimeSupport


def handle_existing_workflow_data(
    args: argparse.Namespace,
    stdout: TextIO,
    stderr: TextIO,
    support: RuntimeSupport,
) -> int | None:
    work_dir = pathlib.Path(args.work_dir)
    if args.rerun_existing:
        validation_error = work_dir_guard_module.validate_rerun_work_dir(work_dir, support)
        if validation_error:
            print(f"[lgwf] {validation_error}", file=stderr)
            return 2
    if not has_existing_lgwf_data(work_dir, support):
        if getattr(args, "resume_existing", False):
            print("[lgwf] --resume-existing requires existing .lgwf checkpoint data. Use --rerun-existing to start over.", file=stderr)
            return 2
        return None

    if args.rerun_existing:
        process_status_module.stop_work_dir_processes(work_dir, stderr, support)
        delete_existing_lgwf_data(work_dir, stderr, support)
        return None
    if getattr(args, "resume_existing", False):
        run_id = args.resume_run_id
        if run_id:
            checkpoint = load_checkpoint(work_dir, run_id, support)
            if checkpoint is None:
                print(f"[lgwf] failed checkpoint not found for run_id={run_id}. Use --rerun-existing to start over.", file=stderr)
                return 2
            if checkpoint.get("status") == "running":
                if has_running_workflow_process(work_dir, support):
                    print(f"[lgwf] running checkpoint still has a live workflow process for run_id={run_id}. Use --continue-existing.", file=stderr)
                    return 2
                args.resume_orphaned_running = True
            elif checkpoint.get("status") not in {"failed", "stopped"}:
                print(f"[lgwf] resumable checkpoint not found for run_id={run_id}. Use --rerun-existing to start over.", file=stderr)
                return 2
        else:
            checkpoint = latest_failed_checkpoint(work_dir, support)
            if checkpoint is None:
                checkpoint = latest_stopped_checkpoint(work_dir, support)
                if checkpoint is None:
                    if has_running_workflow_process(work_dir, support):
                        print("[lgwf] running checkpoint still has a live workflow process. Use --continue-existing.", file=stderr)
                        return 2
                    checkpoint = latest_orphaned_running_checkpoint(work_dir, support)
                    if checkpoint is None:
                        print("[lgwf] no failed, stopped, or orphaned running checkpoint found. Use --rerun-existing to start over.", file=stderr)
                        return 2
                    args.resume_orphaned_running = True
            args.resume_run_id = checkpoint["run_id"]
        return None
    if args.continue_existing:
        return write_existing_workflow_status(work_dir, stdout, support)
    if args.background:
        return write_existing_workflow_choice_required(work_dir, stdout, stderr, support)

    print(
        f"[lgwf] existing workflow data found: {support.workspace_layout.lgwf_dir(work_dir)}",
        file=stderr,
    )
    print(
        "[lgwf] type 'rerun' to clean old work_dir contents and start a new workflow, "
        "or 'continue' to keep the existing workflow running:",
        file=stderr,
    )
    while True:
        try:
            choice = input().strip().lower()
        except EOFError:
            print(
                "[lgwf] existing workflow data requires a choice. Re-run with --rerun-existing or --continue-existing.",
                file=stderr,
            )
            return 2
        if choice == "rerun":
            validation_error = work_dir_guard_module.validate_rerun_work_dir(work_dir, support)
            if validation_error:
                print(f"[lgwf] {validation_error}", file=stderr)
                return 2
            process_status_module.stop_work_dir_processes(work_dir, stderr, support)
            delete_existing_lgwf_data(work_dir, stderr, support)
            return None
        if choice == "continue":
            return write_existing_workflow_status(work_dir, stdout, support)
        print("[lgwf] enter 'rerun' or 'continue'.", file=stderr)


def write_existing_workflow_choice_required(
    work_dir: pathlib.Path,
    stdout: TextIO,
    stderr: TextIO,
    support: RuntimeSupport,
) -> int:
    print(
        "[lgwf] existing workflow data requires a choice. Re-run with --rerun-existing or --continue-existing.",
        file=stderr,
    )
    payload: dict[str, object] = {
        "requires_existing_workflow_decision": True,
        "phase": "existing_data_requires_choice",
        "work_dir": str(work_dir),
        "lgwf_dir": str(support.workspace_layout.lgwf_dir(work_dir)),
        "choices": ["rerun", "continue"],
        "rerun_command_hint": "re-run the same command with --rerun-existing",
        "continue_command_hint": "re-run the same command with --continue-existing",
        "pending_human_requests": process_status_module.pending_human_requests(work_dir, support),
    }
    latest_run = process_status_module.latest_run_record(work_dir, support)
    if latest_run:
        payload["latest_run"] = latest_run
    metadata = process_status_module.latest_process_metadata(work_dir, support)
    if metadata:
        payload["latest_process"] = metadata
    support.json_io.write_json_line(stdout, payload, sort_keys=False)
    return 2


def has_existing_lgwf_data(work_dir: pathlib.Path, support: RuntimeSupport) -> bool:
    lgwf_dir = support.workspace_layout.lgwf_dir(work_dir)
    if not lgwf_dir.is_dir():
        return False
    try:
        next(lgwf_dir.iterdir())
    except StopIteration:
        return False
    except OSError:
        return True
    return True


def latest_failed_checkpoint(work_dir: pathlib.Path, support: RuntimeSupport) -> dict[str, object] | None:
    return latest_checkpoint_with_status(work_dir, support, {"failed"})


def latest_stopped_checkpoint(work_dir: pathlib.Path, support: RuntimeSupport) -> dict[str, object] | None:
    return latest_checkpoint_with_status(work_dir, support, {"stopped"})


def latest_checkpoint_with_status(
    work_dir: pathlib.Path,
    support: RuntimeSupport,
    statuses: set[str],
) -> dict[str, object] | None:
    root = support.workspace_layout.lgwf_dir(work_dir) / "checkpoints"
    if not root.is_dir():
        return None
    candidates: list[tuple[float, dict[str, object]]] = []
    for path in root.glob("*/checkpoint.json"):
        checkpoint = _read_checkpoint(path)
        if checkpoint and checkpoint.get("status") in statuses and isinstance(checkpoint.get("run_id"), str):
            candidates.append((path.stat().st_mtime, checkpoint))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def latest_orphaned_running_checkpoint(work_dir: pathlib.Path, support: RuntimeSupport) -> dict[str, object] | None:
    if has_running_workflow_process(work_dir, support):
        return None
    root = support.workspace_layout.lgwf_dir(work_dir) / "checkpoints"
    if not root.is_dir():
        return None
    candidates: list[tuple[float, dict[str, object]]] = []
    for path in root.glob("*/checkpoint.json"):
        checkpoint = _read_checkpoint(path)
        if checkpoint and checkpoint.get("status") == "running" and isinstance(checkpoint.get("run_id"), str):
            candidates.append((path.stat().st_mtime, checkpoint))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]


def has_running_workflow_process(work_dir: pathlib.Path, support: RuntimeSupport) -> bool:
    metadata = process_status_module.latest_process_metadata(work_dir, support)
    pid = metadata.get("pid") if isinstance(metadata, dict) else None
    return isinstance(pid, int) and process_status_module.is_process_running(pid, support)


def load_checkpoint(work_dir: pathlib.Path, run_id: str, support: RuntimeSupport) -> dict[str, object] | None:
    path = support.workspace_layout.lgwf_dir(work_dir) / "checkpoints" / run_id / "checkpoint.json"
    return _read_checkpoint(path)


def _read_checkpoint(path: pathlib.Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def delete_existing_lgwf_data(work_dir: pathlib.Path, stderr: TextIO, support: RuntimeSupport) -> None:
    work_root = work_dir.expanduser().resolve()
    validate_work_dir_cleanup_target(work_root)
    validation_error = work_dir_guard_module.validate_rerun_work_dir(work_root, support)
    if validation_error:
        raise RuntimeError(validation_error)
    for child in list(work_root.iterdir()):
        child_path = child.resolve()
        if child_path.parent != work_root:
            raise RuntimeError(f"refusing to delete unexpected work_dir child: {child_path}")
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child_path, ignore_errors=True)
        else:
            child.unlink(missing_ok=True)
    print(f"[lgwf] cleaned old workflow work_dir contents: {work_root}", file=stderr)


def validate_work_dir_cleanup_target(work_root: pathlib.Path) -> None:
    if not work_root.is_dir():
        raise RuntimeError(f"work_dir must be an existing directory: {work_root}")
    if work_root.parent == work_root:
        raise RuntimeError(f"refusing to clean filesystem root: {work_root}")


def write_existing_workflow_status(work_dir: pathlib.Path, stdout: TextIO, support: RuntimeSupport) -> int:
    metadata = process_status_module.latest_process_metadata(work_dir, support)
    if metadata and isinstance(metadata.get("pid"), int):
        return process_status_module.write_process_status(metadata["pid"], str(work_dir), stdout, support)

    status: dict[str, object] = {
        "running": False,
        "phase": "existing_data",
        "work_dir": str(work_dir),
        "pending_human_requests": process_status_module.pending_human_requests(work_dir, support),
    }
    latest_run = process_status_module.latest_run_record(work_dir, support)
    if latest_run:
        status["latest_run"] = latest_run
    support.json_io.write_json_line(stdout, status, sort_keys=False)
    return 0
