from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state, read_json


def choose_route(report: dict, decision: dict | None = None) -> str:
    decision = decision or {}
    status = report.get("status")
    stop_reason = report.get("stop_reason") or decision.get("stop_reason")
    if status == "finished" and stop_reason == "repair_candidate_ready":
        return "promote"
    return "finish"


def main() -> None:
    root = lgwf_dir()
    report = read_json(root / "loops" / "repair_target" / "report.json", {})
    if not isinstance(report, dict):
        report = {}
    decision = read_json(root / "target_repair" / "current" / "decision.json", {})
    if not isinstance(decision, dict):
        decision = {}
    route = choose_route(report, decision)
    append_history({"event": "route_after_repair_agent_loop", "route": route, "status": report.get("status")})
    output_state({"repair_agent_loop_route": route}, next_key=route, route_node="route_after_repair_agent_loop")


if __name__ == "__main__":
    main()
