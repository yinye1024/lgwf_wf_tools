from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, read_json, write_json


def design_ready(proposal: dict[str, Any], review: dict[str, Any]) -> bool:
    return (
        isinstance(proposal.get("prompt_upgrades"), list)
        and bool(proposal["prompt_upgrades"])
        and review.get("passed") is True
        and review.get("ready_for_confirmation") is True
        and not review.get("blocking_issues")
    )


def main() -> None:
    root = lgwf_dir() / "prompt_upgrade"
    proposal = read_json(root / "proposal.json", {})
    review = read_json(root / "proposal_review.json", {})
    if not isinstance(proposal, dict):
        proposal = {}
    if not isinstance(review, dict):
        review = {}
    result = {"next": "exit" if design_ready(proposal, review) else "continue"}
    write_json(root / "design_decision.json", result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
