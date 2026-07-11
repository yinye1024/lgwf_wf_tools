from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import read_json, write_json


def build_context(root: Path) -> dict[str, object]:
    lgwf_dir = root / ".lgwf"
    proposal = read_json(lgwf_dir / "verification_plan_proposal.json")
    change_context = read_json(lgwf_dir / "change_context.json")
    impact = read_json(lgwf_dir / "impact_classification.json")
    review_context_json = {
        "review_node": "confirm_verification_plan",
        "approval_target": "verification_plan_proposal",
        "approve_writes": ".lgwf/verification_plan.json",
        "persist_path": ".lgwf/verification_plan_approval.json",
        "allowed_decisions": ["approve", "revise", "reject"],
        "proposal": proposal,
    }
    context = {
        "review_node": "confirm_verification_plan",
        "approval_target": "verification_plan_proposal",
        "approve_writes": ".lgwf/verification_plan.json",
        "persist_path": ".lgwf/verification_plan_approval.json",
        "allowed_decisions": ["approve", "revise", "reject"],
        "proposal": proposal,
        "change_summary": {
            "change_source": change_context.get("change_source"),
            "files": [item.get("path") for item in change_context.get("files", []) if isinstance(item, dict)],
        },
        "impact_summary": {
            "risk": impact.get("risk"),
            "categories": impact.get("categories", []),
            "impacted_workflows": impact.get("impacted_workflows", []),
            "ambiguities": impact.get("ambiguities", []),
        },
        "review_context_json": review_context_json,
        "notes": [
            "approve 只固化当前 proposal，不自动新增命令。",
            "revise 必须提交包含完整 proposal 的 review_context_json。",
            "reject 将在子 workflow 内 FAIL_ALL。"
        ],
    }
    return context


def main() -> None:
    root = Path.cwd()
    context = build_context(root)
    write_json(root / ".lgwf" / "verification_plan_confirmation_context.json", context)
    print(
        json.dumps(
            {"wf_maintenance_gate.verification_plan_confirmation_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
