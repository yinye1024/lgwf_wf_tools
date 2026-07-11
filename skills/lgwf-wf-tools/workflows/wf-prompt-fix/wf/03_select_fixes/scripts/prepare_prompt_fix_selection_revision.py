from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, read_json, write_json


def _decision_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, dict):
        for key in ("value", "approval", "decision", "route"):
            decision = _decision_value(value.get(key))
            if decision:
                return decision
    return ""


def review_decision(approval: dict[str, Any]) -> str:
    for key in ("approval", "decision", "route"):
        decision = _decision_value(approval.get(key))
        if decision:
            return decision
    return ""


def resolve_revised_context(approval: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    if review_decision(approval) != "revise":
        raise ValueError("只有 review revise 才能更新 prompt 修复选择上下文")
    revised_value = approval.get("value")
    if not isinstance(revised_value, dict):
        raise TypeError("review revise 必须提交完整 JSON object")
    revised = dict(previous)
    revised.update(revised_value)
    revised["latest_revision_comment"] = str(approval.get("comment") or "")
    return revised


def main() -> None:
    root = lgwf_dir() / "prompt_acceptance"
    approval = read_json(root / "fix_selection_review.json", {})
    previous = read_json(root / "fix_selection_review_context.json", {})
    if not isinstance(approval, dict):
        approval = {}
    if not isinstance(previous, dict):
        previous = {}
    revised = resolve_revised_context(approval, previous)
    write_json(root / "fix_selection_review_context.json", revised)
    output_state({"prompt_fix_selection_review_context": revised})


if __name__ == "__main__":
    main()
