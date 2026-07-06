from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, output_state, read_json, write_json


def main() -> None:
    decision = read_json(lgwf_dir() / "initial_audit_diagnostics.json", {})
    route = "run" if not decision.get("passed") else "skip"
    placeholder = {
        "passed": False,
        "issues": [],
        "summary": "candidate observe 初始占位结果；等待真实 candidate audit 写入。",
    }
    write_json(lgwf_dir() / "latest_candidate_audit_result.json", placeholder)
    output_state({"candidate_loop_entry": {"route": route}}, next_key=route, route_node="route_candidate_loop_entry")


if __name__ == "__main__":
    main()
