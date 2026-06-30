from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, read_json


def choose_route(decision: dict) -> str:
    if decision.get("reject"):
        return "reject"
    return "apply" if decision.get("approve") and decision.get("approved_upgrade_ids") else "summarize"


def main() -> None:
    decision = read_json(lgwf_dir() / "prompt_upgrade" / "decision.json", {})
    if not isinstance(decision, dict):
        decision = {}
    route = choose_route(decision)
    output_state({"prompt_upgrade_route": route}, next_key=route, route_node="route_after_prompt_upgrade_decision")


if __name__ == "__main__":
    main()

