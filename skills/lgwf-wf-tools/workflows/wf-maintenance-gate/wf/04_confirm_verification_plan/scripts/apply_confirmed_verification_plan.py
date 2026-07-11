from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import read_json, write_json


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    approval = read_json(lgwf_dir / "verification_plan_approval.json")
    if approval.get("approval") != "approve":
        raise ValueError("只有 approve 才能固化 verification_plan")
    proposal = read_json(lgwf_dir / "verification_plan_proposal.json")
    confirmed = {
        "artifact_kind": "confirmed_verification_plan",
        "source_proposal_file": ".lgwf/verification_plan_proposal.json",
        "source_approval_file": ".lgwf/verification_plan_approval.json",
        "confirmed": proposal,
    }
    write_json(lgwf_dir / "verification_plan.json", confirmed)
    print(
        json.dumps(
            {"wf_maintenance_gate.confirmed_verification_plan": confirmed},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
