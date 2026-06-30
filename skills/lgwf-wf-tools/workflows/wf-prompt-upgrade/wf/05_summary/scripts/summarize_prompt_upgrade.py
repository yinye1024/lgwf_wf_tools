from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, read_json, write_json


def build_summary(
    *,
    inventory: dict[str, Any],
    proposal: dict[str, Any],
    decision: dict[str, Any],
    review: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    prompts = inventory.get("prompts") if isinstance(inventory.get("prompts"), list) else []
    upgrades = proposal.get("prompt_upgrades") if isinstance(proposal.get("prompt_upgrades"), list) else []
    approved = decision.get("approved_upgrade_ids") if isinstance(decision.get("approved_upgrade_ids"), list) else []
    if not upgrades:
        status = "no_upgrades_proposed"
    elif decision.get("reject"):
        status = "rejected"
    elif review.get("passed") is True and not review.get("remaining_upgrade_ids"):
        status = "upgraded"
    else:
        status = "needs_attention"
    return {
        "status": status,
        "artifact_root": ".lgwf/prompt_upgrade",
        "root_summary_path": ".lgwf/target_prompt_upgrade_summary.json",
        "prompt_count": len(prompts),
        "upgrade_count": len(upgrades),
        "approved_upgrade_ids": approved,
        "remaining_upgrade_ids": review.get("remaining_upgrade_ids", []),
        "files_to_modify": proposal.get("files_to_modify", []),
        "summary": review.get("summary") or proposal.get("summary") or "",
        "history": history,
    }


def main() -> None:
    root = lgwf_dir()
    upgrade_root = root / "prompt_upgrade"
    inventory = read_json(upgrade_root / "inventory.json", {})
    proposal = read_json(upgrade_root / "proposal.json", {})
    decision = read_json(upgrade_root / "decision.json", {})
    review = read_json(upgrade_root / "apply_review.json", {})
    history = read_json(upgrade_root / "react_history.json", [])
    if not isinstance(inventory, dict):
        inventory = {}
    if not isinstance(proposal, dict):
        proposal = {}
    if not isinstance(decision, dict):
        decision = {}
    if not isinstance(review, dict):
        review = {}
    if not isinstance(history, list):
        history = []
    summary = build_summary(inventory=inventory, proposal=proposal, decision=decision, review=review, history=history)
    write_json(root / "target_prompt_upgrade_summary.json", summary)
    write_json(upgrade_root / "summary.json", summary)
    output_state({"prompt_upgrade_summary": summary})


if __name__ == "__main__":
    main()

