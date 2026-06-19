from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import (
    append_history,
    lgwf_dir,
    load_self_fix_target,
    output_state,
    read_json,
    read_text,
    run_lgwf,
    write_json,
)


def parse_status(stdout: str) -> dict:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {"raw_stdout": stdout}
    return data if isinstance(data, dict) else {"value": data}


def latest_run_summary(work_dir: Path) -> dict:
    listed = run_lgwf(["runs", "list", "--work-dir", str(work_dir), "--limit", "1"], timeout=60)
    if listed.returncode != 0:
        return {"list_error": listed.stderr, "list_stdout": listed.stdout}
    try:
        data = json.loads(listed.stdout)
    except json.JSONDecodeError:
        return {"list_stdout": listed.stdout}
    runs = data.get("runs") if isinstance(data, dict) else None
    if not runs:
        return {"runs": data}
    run_id = runs[0].get("run_id") or runs[0].get("id")
    result: dict = {"latest_run": runs[0]}
    if run_id:
        summary = run_lgwf(["runs", "summary", "--work-dir", str(work_dir), "--run-id", str(run_id)], timeout=60)
        changed = run_lgwf(["runs", "changed", "--work-dir", str(work_dir), "--run-id", str(run_id)], timeout=60)
        result["summary_stdout"] = summary.stdout
        result["summary_stderr"] = summary.stderr
        result["changed_stdout"] = changed.stdout
        result["changed_stderr"] = changed.stderr
    return result


def main() -> None:
    root = lgwf_dir()
    target = load_self_fix_target()
    current = read_json(root / "target_current_run.json", {})
    work_dir = Path(current.get("work_dir") or target.get("last_attempt_dir") or "")
    if not work_dir:
        raise ValueError("missing current target workflow work_dir")
    pid = current.get("pid")
    status_args = ["status", "--work-dir", str(work_dir)]
    if pid:
        status_args.extend(["--pid", str(pid)])
    status_proc = run_lgwf(status_args, timeout=120)
    status = parse_status(status_proc.stdout)
    status["status_returncode"] = status_proc.returncode
    status["status_stderr"] = status_proc.stderr

    phase = status.get("phase")
    running = status.get("running")
    pending = status.get("pending_human_requests") or []
    request_id = status.get("human_request_id")
    if not request_id and pending and isinstance(pending, list):
        first = pending[0] if pending else {}
        if isinstance(first, dict):
            request_id = first.get("request_id")

    if phase == "waiting_human" or request_id:
        approval = {
            "attempt": target.get("current_attempt"),
            "work_dir": str(work_dir),
            "request_id": request_id,
            "status": status,
        }
        if request_id:
            got = run_lgwf(["approval", "get", "--work-dir", str(work_dir), "--request-id", str(request_id)], timeout=60)
            approval["request_stdout"] = got.stdout
            approval["request_stderr"] = got.stderr
            try:
                approval["request"] = json.loads(got.stdout)
            except json.JSONDecodeError:
                approval["request"] = {"raw": got.stdout}
        write_json(root / "target_approval_context.json", approval)
        target["last_status"] = "waiting_approval"
        write_json(root / "self_fix_target.json", target)
        output_state({"target": target, "target_approval_context": approval, "next_action": "approval"})
        return

    completed = running is False or phase in {"completed", "failed"}
    if not completed:
        wait_proc = run_lgwf(["wait"], timeout=90)
        append_history({"event": "target_still_running", "attempt": target.get("current_attempt"), "phase": phase})
        output_state({"target": target, "last_observe_status": status, "wait_stdout": wait_proc.stdout, "next_action": "observe"})
        return

    log_file = Path(current.get("log_file") or work_dir / "target-workflow.log")
    summary = latest_run_summary(work_dir)
    failed = phase == "failed" or bool(status.get("last_error")) or status_proc.returncode != 0
    if failed:
        review = {
            "attempt": target.get("current_attempt"),
            "phase": phase,
            "work_dir": str(work_dir),
            "status": status,
            "log_tail": read_text(log_file, limit=20000),
            "run_artifacts": summary,
        }
        write_json(root / "target_failure_review.json", review)
        target["last_status"] = "failed"
        append_history({"event": "target_failed", "attempt": target.get("current_attempt"), "phase": phase})
        write_json(root / "self_fix_target.json", target)
        output_state({"target": target, "target_failure_review": review, "next_action": "fix"})
        return

    target["last_status"] = "succeeded"
    target["success_attempt"] = target.get("current_attempt")
    write_json(root / "self_fix_target.json", target)
    append_history({"event": "target_succeeded", "attempt": target.get("current_attempt")})
    output_state({"target": target, "last_observe_status": status, "run_artifacts": summary, "next_action": "finish"})


if __name__ == "__main__":
    main()
