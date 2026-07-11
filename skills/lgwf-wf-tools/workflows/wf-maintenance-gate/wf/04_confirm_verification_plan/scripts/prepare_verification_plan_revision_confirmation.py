from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import read_json, write_json
from prepare_verification_plan_confirmation import build_context


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    approval = read_json(lgwf_dir / "verification_plan_approval.json")
    if approval.get("approval") != "revise":
        raise ValueError("只有 revise 才能重建验证计划确认上下文")

    review_context = approval.get("review_context_json", {})
    if isinstance(review_context, dict) and isinstance(review_context.get("proposal"), dict):
        write_json(lgwf_dir / "verification_plan_proposal.json", review_context["proposal"])

    context = build_context(root)
    context["latest_revision_request"] = approval
    write_json(lgwf_dir / "verification_plan_confirmation_context.json", context)
    print(
        json.dumps(
            {"wf_maintenance_gate.verification_plan_confirmation_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
