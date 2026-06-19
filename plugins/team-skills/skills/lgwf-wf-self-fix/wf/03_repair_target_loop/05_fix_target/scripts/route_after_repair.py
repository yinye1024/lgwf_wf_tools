from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state, read_json


def choose_route(plan: dict, validation: dict, change_audit: dict | None = None) -> str:
    if plan.get("status") == "blocked":
        return "finish"
    if change_audit is not None and change_audit.get("passed") is not True:
        return "finish"
    if validation.get("passed") is not True:
        return "finish"
    return "rerun"


def main() -> None:
    root = lgwf_dir()
    plan = read_json(root / "target_repair_plan.json", {})
    validation = read_json(root / "target_repair_validation.json", {})
    change_audit = read_json(root / "target_repair_change_audit.json", {})
    if not isinstance(plan, dict):
        plan = {}
    if not isinstance(validation, dict):
        validation = {}
    if not isinstance(change_audit, dict):
        change_audit = {}
    route = choose_route(plan, validation, change_audit)
    append_history(
        {
            "event": "route_after_repair",
            "route": route,
            "plan_status": plan.get("status"),
            "change_audit_passed": change_audit.get("passed"),
            "validation_passed": validation.get("passed"),
        }
    )
    output_state({"repair_route": route}, next_key=route)


if __name__ == "__main__":
    main()
