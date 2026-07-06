from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import lgwf_dir, output_state, read_json


def main() -> None:
    initial = read_json(lgwf_dir() / "initial_audit_diagnostics.json", {})
    candidate = read_json(lgwf_dir() / "candidate_pass_snapshot.json", {})
    route = "summary" if initial.get("passed") or not candidate else "promote"
    output_state({"promote_entry_route": route}, next_key=route, route_node="route_promote_entry")


if __name__ == "__main__":
    main()
