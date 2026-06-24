from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state
from target_repair_loop import load_current_artifact


def choose_route(verification: dict[str, Any]) -> str:
    if verification.get("passed") is True and verification.get("semantic_review_needed") is True:
        return "review"
    return "finish"


def main() -> None:
    root = lgwf_dir()
    verification = load_current_artifact(root, "verification", {})
    if not isinstance(verification, dict):
        verification = {}
    route = choose_route(verification)
    append_history(
        {
            "event": "route_after_verification",
            "route": route,
            "passed": verification.get("passed"),
            "semantic_review_needed": verification.get("semantic_review_needed"),
        }
    )
    output_state({"verify_repair_route": route}, next_key=route, route_node="route_after_verification")


if __name__ == "__main__":
    main()
