"""固化已确认的打包计划。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from confirmation_io import unwrap_approval
from packaging_common import load_lgwf_artifact, write_json


def main() -> None:
    root = Path.cwd()
    approval = unwrap_approval(
        load_lgwf_artifact(root, "packaging_plan_approval.json"),
        "packaging_plan_approval",
    )
    if approval["approval"] != "approve":
        raise ValueError("只有 approve 才能固化 confirmed_packaging_plan")
    proposal = load_lgwf_artifact(root, "packaging_plan_proposal.json")
    confirmed = {
        "artifact_kind": "confirmed_packaging_plan",
        "source_proposal_file": ".lgwf/packaging_plan_proposal.json",
        "source_approval_file": ".lgwf/packaging_plan_approval.json",
        "confirmed": proposal,
    }
    write_json(root / ".lgwf" / "confirmed_packaging_plan.json", confirmed)
    print(
        json.dumps(
            {"skill_packaging.confirmed_packaging_plan": confirmed},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
