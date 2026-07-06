from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, output_state, read_json


def main() -> None:
    latest = read_json(lgwf_dir() / "latest_candidate_audit_result.json", {})
    runtime = read_json(lgwf_dir() / "runtime_context.json", {})
    history = read_json(lgwf_dir() / "candidate_attempt_log.json", [])
    max_attempts = int(runtime.get("attempt_policy", {}).get("max_attempts", 5))
    if latest.get("passed"):
        decision = {"category": "finish", "reason": "candidate_audit_passed", "passed": True}
        reason = "candidate_audit_passed"
    elif len(history) >= max_attempts:
        decision = {"category": "finish", "reason": "max_attempts_reached", "passed": False}
        reason = "max_attempts_reached"
    else:
        decision = {"category": "continue", "reason": "candidate_audit_failed", "passed": False}
        reason = "candidate_audit_failed"
    output_state({"candidate_repair_loop_decision": decision, "loop_exit_reason": reason})


if __name__ == "__main__":
    main()
