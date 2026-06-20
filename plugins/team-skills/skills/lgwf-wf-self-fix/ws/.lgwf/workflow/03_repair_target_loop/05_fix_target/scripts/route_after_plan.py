from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state, read_json


def choose_route(plan: dict, review: dict) -> str:
    if plan.get("status") != "ready":
        return "finish"
    if review.get("passed") is not True or review.get("approved_to_apply") is not True:
        return "finish"
    return "apply"


def main() -> None:
    root = lgwf_dir()
    plan = read_json(root / "target_repair_plan.json", {})
    review = read_json(root / "target_repair_plan_review.json", {})
    if not isinstance(plan, dict):
        plan = {}
    if not isinstance(review, dict):
        review = {}
    route = choose_route(plan, review)
    append_history(
        {
            "event": "route_after_plan",
            "route": route,
            "plan_status": plan.get("status"),
            "review_passed": review.get("passed"),
        }
    )
    output_state({"repair_plan_route": route}, next_key=route, route_node="route_after_plan")


if __name__ == "__main__":
    main()
