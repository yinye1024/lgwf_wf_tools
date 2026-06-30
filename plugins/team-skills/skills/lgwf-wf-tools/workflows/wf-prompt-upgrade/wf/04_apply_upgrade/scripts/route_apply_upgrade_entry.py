from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, read_json, write_json


def choose_route(decision: dict) -> str:
    if decision.get("approve") and decision.get("approved_upgrade_ids"):
        return "apply"
    return "skip"


def ensure_observe_feedback_placeholder() -> None:
    path = lgwf_dir() / "prompt_upgrade" / "apply_review.json"
    if path.exists():
        return
    write_json(
        path,
        {
            "passed": False,
            "issues": [],
            "summary": "首轮默认 observe 占位文件；等待 OBSERVE 阶段写入真实验收结果。",
            "initial_placeholder": True,
        },
    )


def main() -> None:
    decision = read_json(lgwf_dir() / "prompt_upgrade" / "decision.json", {})
    if not isinstance(decision, dict):
        decision = {}
    route = choose_route(decision)
    if route == "apply":
        ensure_observe_feedback_placeholder()
    output_state({"prompt_upgrade_apply_entry_route": route}, next_key=route, route_node="route_apply_upgrade_entry")


if __name__ == "__main__":
    main()
