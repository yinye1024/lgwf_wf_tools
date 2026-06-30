from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, read_json, write_json


def choose_route(selection: dict) -> str:
    if selection.get("skip_fix"):
        return "skip"
    if selection.get("selected_issue_ids"):
        return "fix"
    return "skip"


def ensure_observe_feedback_placeholder() -> None:
    path = lgwf_dir() / "prompt_acceptance" / "repair_review.json"
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
    selection = read_json(lgwf_dir() / "prompt_acceptance" / "fix_selection.json", {})
    if not isinstance(selection, dict):
        selection = {}
    route = choose_route(selection)
    if route == "fix":
        ensure_observe_feedback_placeholder()
    output_state({"prompt_repair_entry_route": route}, next_key=route, route_node="route_repair_loop_entry")


if __name__ == "__main__":
    main()
