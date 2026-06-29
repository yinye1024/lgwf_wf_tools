from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, read_json


def _has_items(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def choose_route(summary: dict[str, Any]) -> str:
    clean_audit = (
        summary.get("status") == "passed"
        and summary.get("audit_passed") is True
        and not _has_items(summary.get("remaining_issue_ids"))
    )
    repair_clean = (
        summary.get("status") == "fixed"
        and summary.get("repair_passed") is True
        and not _has_items(summary.get("remaining_issue_ids"))
    )
    has_unexpected_changes = (
        _has_items(summary.get("unexpected_changes"))
        or _has_items(summary.get("unexpected_change_ids"))
        or _has_items(summary.get("unplanned_changes"))
    )
    if (clean_audit or repair_clean) and not has_unexpected_changes:
        return "auto_finish"
    return "confirm"


def main() -> None:
    root = lgwf_dir() / "prompt_acceptance"
    summary = read_json(root / "summary.json", {})
    if not isinstance(summary, dict):
        summary = {}
    route = choose_route(summary)
    output_state(
        {"prompt_acceptance_summary_route": route},
        next_key=route,
        route_node="route_after_prompt_acceptance_summary",
    )


if __name__ == "__main__":
    main()
