from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import append_attempt_log, lgwf_dir, output_state, read_json, run_audit, summarize_audit_result, write_json


def main() -> None:
    runtime = read_json(lgwf_dir() / "runtime_context.json", {})
    workflow_path = Path(str(runtime["candidate_workspace_plan"]["candidate_workflow_lgwf"]))
    result = run_audit(workflow_path)
    summary = summarize_audit_result(result, label="candidate")
    write_json(lgwf_dir() / "latest_candidate_audit_result.json", summary)
    if summary["passed"]:
        snapshot = {
            "candidate_workflow_lgwf": str(workflow_path),
            "candidate_package_root": str(workflow_path.parent.parent),
            "diagnostics": summary,
        }
        write_json(lgwf_dir() / "candidate_pass_snapshot.json", snapshot)
    history = append_attempt_log({"event": "candidate_audit", "passed": summary["passed"], "issue_count": summary["issue_count"]})
    output_state(
        {
            "latest_candidate_audit_result": summary,
            "candidate_attempt_log": history,
            "candidate_verify_result": {
                "passed": summary["passed"],
                "summary": summary["summary"],
                "issue_count": summary["issue_count"],
            },
        }
    )


if __name__ == "__main__":
    main()
