from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, output_state, read_json


def main() -> None:
    diagnostics = read_json(lgwf_dir() / "initial_audit_diagnostics.json", {})
    route = "summary" if diagnostics.get("passed") else "candidate"
    entry_decision = {"route": route, "passed": bool(diagnostics.get("passed")), "summary": diagnostics.get("summary", "")}
    output_state({"entry_decision": entry_decision}, next_key=route, route_node="route_initial_audit_decision")


if __name__ == "__main__":
    main()
