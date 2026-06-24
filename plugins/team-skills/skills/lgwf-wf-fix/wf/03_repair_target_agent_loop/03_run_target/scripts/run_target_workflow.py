from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import (
    append_history,
    attempt_dir,
    lgwf_dir,
    load_self_fix_target,
    output_state,
    read_json,
    run_lgwf,
    write_json,
)
from target_repair_loop import start_iteration, write_current_artifact


def main() -> None:
    target = load_self_fix_target()
    attempt = int(target.get("current_attempt", 0)) + 1
    target["current_attempt"] = attempt
    target["last_status"] = "running"
    root = lgwf_dir()
    start_iteration(root, target)
    work_dir = attempt_dir(attempt)
    work_dir.mkdir(parents=True, exist_ok=True)
    target_input = read_json(lgwf_dir() / "target_workflow_input.json", {})
    if not isinstance(target_input, dict):
        raise ValueError(".lgwf/target_workflow_input.json must contain a JSON object")

    input_json = json.dumps(target_input, ensure_ascii=False)
    log_file = work_dir / "target-workflow.log"
    pid_file = work_dir / "target-workflow.pid.json"
    proc = run_lgwf(
        [
            "run",
            "--workflow-lgwf",
            target["target_workflow_lgwf"],
            "--work-dir",
            str(work_dir),
            "--input-json",
            input_json,
            "--background",
            "--log-file",
            str(log_file),
            "--pid-file",
            str(pid_file),
            "--rerun-existing",
        ],
        timeout=180,
    )
    if proc.returncode != 0:
        failure = {
            "attempt": attempt,
            "phase": "start_failed",
            "status": "failed",
            "failure_class": "runtime_failure",
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "work_dir": str(work_dir),
            "log_file": str(log_file),
        }
        write_current_artifact(root, "run", failure)
        write_current_artifact(root, "observation", failure)
        target["last_status"] = "failed"
        target["last_attempt_dir"] = str(work_dir)
        write_json(root / "self_fix_target.json", target)
        append_history({"event": "target_start_failed", "attempt": attempt, "returncode": proc.returncode})
        output_state({"target": target, "last_attempt": failure, "next_action": "fix"})
        return

    try:
        metadata = json.loads(proc.stdout)
    except json.JSONDecodeError:
        metadata = {"stdout": proc.stdout}
    metadata.update({"attempt": attempt, "work_dir": str(work_dir), "log_file": str(log_file), "pid_file": str(pid_file)})
    metadata["status"] = "running"
    target["last_attempt"] = metadata
    target["last_attempt_dir"] = str(work_dir)
    write_json(root / "self_fix_target.json", target)
    write_current_artifact(root, "run", metadata)
    append_history({"event": "target_started", "attempt": attempt, "work_dir": str(work_dir)})
    output_state({"target": target, "current_run": metadata, "next_action": "observe"})


if __name__ == "__main__":
    main()
