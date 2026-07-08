from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, output_state, read_json, summarize_audit_result, write_json


def main() -> None:
    result = read_json(lgwf_dir() / "post_promote_real_audit_result.json", {})
    summary = summarize_audit_result(result, label="post_promote_real")
    final_status = "success" if summary["passed"] else "failed"
    diagnostics = {"final_status_candidate_or_target": final_status, "final_diagnostics": summary}
    write_json(lgwf_dir() / "final_diagnostics.json", diagnostics)
    output_state(diagnostics)


if __name__ == "__main__":
    main()
