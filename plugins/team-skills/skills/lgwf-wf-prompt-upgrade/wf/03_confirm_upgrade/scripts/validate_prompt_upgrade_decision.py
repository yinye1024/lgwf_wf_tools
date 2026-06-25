from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, read_json, write_json


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
    proposal = read_json(root / "proposal.json", {})
    if not isinstance(decision, dict):
        decision = {}
    if not isinstance(proposal, dict):
        proposal = {}
    normalized = normalize_decision(decision, proposal)
    write_json(root / "decision.json", normalized)
    output_state({"prompt_upgrade_decision": normalized})


if __name__ == "__main__":
    main()

