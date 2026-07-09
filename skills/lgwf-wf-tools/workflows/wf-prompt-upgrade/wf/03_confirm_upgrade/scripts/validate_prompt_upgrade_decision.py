from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, read_json, write_json


def _decision_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, dict):
        for key in ("value", "approval", "decision", "route"):
            decision = _decision_value(value.get(key))
            if decision:
                return decision
    return ""


def review_decision(review: dict[str, Any]) -> str:
    for key in ("approval", "decision", "route"):
        decision = _decision_value(review.get(key))
        if decision:
            return decision
    return ""


def decision_from_review(review: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    decision = review_decision(review)
    comment = review.get("comment", "") if isinstance(review.get("comment"), str) else ""
    if decision == "approve":
        return {"approve": True, "approved_upgrade_ids": [], "reject": False, "comment": comment}
    if decision == "reject":
        return {"approve": False, "approved_upgrade_ids": [], "reject": True, "comment": comment}
    if decision == "revise":
        value = review.get("value")
        if isinstance(value, dict):
            merged = dict(value)
            if comment and not isinstance(merged.get("comment"), str):
                merged["comment"] = comment
            return merged
        return fallback
    return fallback


def normalize_decision(decision: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    upgrades = proposal.get("prompt_upgrades") if isinstance(proposal.get("prompt_upgrades"), list) else []
    valid_ids = [item.get("id") for item in upgrades if isinstance(item, dict) and isinstance(item.get("id"), str)]
    valid_id_set = set(valid_ids)
    reject = bool(decision.get("reject")) or bool(decision.get("skip_apply"))
    approve = bool(decision.get("approve")) and not reject
    raw_ids = decision.get("approved_upgrade_ids")
    approved_ids = [item for item in raw_ids if isinstance(item, str) and item in valid_id_set] if isinstance(raw_ids, list) else []
    if approve and not approved_ids:
        approved_ids = valid_ids
    return {
        "approve": approve,
        "reject": reject or not approve,
        "approved_upgrade_ids": approved_ids,
        "comment": decision.get("comment", "") if isinstance(decision.get("comment"), str) else "",
    }


def main() -> None:
    root = lgwf_dir() / "prompt_upgrade"
    decision = read_json(root / "decision.json", {})
    review = read_json(root / "decision_review.json", {})
    proposal = read_json(root / "proposal.json", {})
    if not isinstance(decision, dict):
        decision = {}
    if not isinstance(review, dict):
        review = {}
    if not isinstance(proposal, dict):
        proposal = {}
    decision = decision_from_review(review, decision)
    normalized = normalize_decision(decision, proposal)
    write_json(root / "decision.json", normalized)
    output_state({"prompt_upgrade_decision": normalized})


if __name__ == "__main__":
    main()

