from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, output_state, read_json, write_json


def main() -> None:
    initial = read_json(lgwf_dir() / "initial_audit_diagnostics.json", {})
    candidate_history = read_json(lgwf_dir() / "candidate_attempt_log.json", [])
    promote_result = read_json(lgwf_dir() / "promote_result.json", {})
    final_info = read_json(lgwf_dir() / "final_diagnostics.json", {})

    if initial.get("passed"):
        final_audit_status = "passed_initial_real_audit"
        final_diagnostics = initial
    else:
        final_audit_status = final_info.get("final_status_candidate_or_target", "failed")
        final_diagnostics = final_info.get("final_diagnostics") or read_json(lgwf_dir() / "latest_candidate_audit_result.json", {})

    summary = {
        "result_summary": {
            "final_audit_status": final_audit_status,
            "attempt_count": len(candidate_history),
            "promote_history": [promote_result] if promote_result else [],
            "last_diagnostics": final_diagnostics,
        },
        "final_audit_status": final_audit_status,
        "attempt_count": len(candidate_history),
        "promote_history": [promote_result] if promote_result else [],
    }
    write_json(lgwf_dir() / "result_summary.json", summary)
    output_state(summary)


if __name__ == "__main__":
    main()
