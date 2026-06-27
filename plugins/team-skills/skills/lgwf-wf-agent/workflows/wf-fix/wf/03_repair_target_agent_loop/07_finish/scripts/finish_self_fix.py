from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state
from target_repair_loop import finish_loop, load_current_artifact


def main() -> None:
    root = lgwf_dir()
    target = load_self_fix_target()
    decision = load_current_artifact(root, "decision", {})
    observation = load_current_artifact(root, "observation", {})
    verification = load_current_artifact(root, "verification", {})
    change_audit = load_current_artifact(root, "change_audit", {})
    if not isinstance(decision, dict):
        decision = {}
    if not isinstance(observation, dict):
        observation = {}

    if decision.get("category") == "block":
        status = "block"
        stop_reason = str(decision.get("stop_reason") or "unknown_blocker")
        success = False
    elif target.get("last_status") == "succeeded":
        stop_reason = str(decision.get("stop_reason") or "target_succeeded")
        status = "finish_degraded" if stop_reason == "target_succeeded_with_warnings" else "finish_success"
        success = True
    else:
        status = "block"
        stop_reason = str(decision.get("stop_reason") or "unknown_blocker")
        success = False

    report = finish_loop(
        root,
        status=status,
        stop_reason=stop_reason,
        report={
            "target_workflow_lgwf": target.get("target_workflow_lgwf"),
            "attempts": target.get("current_attempt"),
            "observation": observation,
            "verification": verification if isinstance(verification, dict) else {},
            "change_audit": change_audit if isinstance(change_audit, dict) else {},
        },
    )
    append_history({"event": "repair_loop_finished", "success": success, "status": status, "stop_reason": stop_reason})
    output_state({"repair_loop_finished": True, "success": success, "target_repair_report": report})


if __name__ == "__main__":
    main()
