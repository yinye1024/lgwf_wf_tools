from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, read_json, write_json


def build_confirmation_context(
    inventory: dict[str, Any],
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    prompts = inventory.get("prompts") if isinstance(inventory.get("prompts"), list) else []
    upgrades = proposal.get("prompt_upgrades") if isinstance(proposal.get("prompt_upgrades"), list) else []
    return {
        "artifact_root": ".lgwf/prompt_upgrade",
        "prompt_count": len(prompts),
        "upgrade_count": len(upgrades),
        "ready_for_confirmation": review.get("passed") is True and review.get("ready_for_confirmation") is True,
        "proposal_summary": proposal.get("summary", ""),
        "target_outcome": proposal.get("target_outcome", ""),
        "prompt_upgrades": upgrades,
        "files_to_modify": proposal.get("files_to_modify", []),
        "risks": proposal.get("risks", []),
        "review": review,
        "analysis_summary": analysis.get("summary", ""),
        "instructions": {
            "approve": "Set true to apply the proposed prompt upgrades.",
            "approved_upgrade_ids": "Leave empty when approving all proposed upgrades; otherwise list upgrade ids to apply.",
            "reject": "Set true to reject the upgrade proposal and stop the run via FAIL_ALL.",
            "comment": "Optional operator note.",
        },
    }


def main() -> None:
    root = lgwf_dir() / "prompt_upgrade"
    inventory = read_json(root / "inventory.json", {})
    analysis = read_json(root / "analysis.json", {})
    proposal = read_json(root / "proposal.json", {})
    review = read_json(root / "proposal_review.json", {})
    for value_name, value in (("inventory", inventory), ("analysis", analysis), ("proposal", proposal), ("review", review)):
        if not isinstance(value, dict):
            raise ValueError(f"{value_name} must be a JSON object")
    context = build_confirmation_context(inventory, analysis, proposal, review)
    write_json(root / "confirmation_context.json", context)
    output_state({"prompt_upgrade_confirmation_context": context})


if __name__ == "__main__":
    main()

