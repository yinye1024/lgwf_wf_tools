from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import lgwf_dir, read_json, write_json


def choose_next(selection: dict[str, Any], review: dict[str, Any]) -> str:
    if selection.get("skip_fix"):
        return "exit"
    selected = {str(item) for item in selection.get("selected_issue_ids", []) if str(item)}
    remaining = {str(item) for item in review.get("remaining_issue_ids", []) if str(item)}
    if selected and review.get("passed") is True and not remaining:
        return "exit"
    return "continue"


def append_react_history(root: Path, event: dict[str, Any]) -> list[dict[str, Any]]:
    path = root / "react_history.json"
    history = read_json(path, [])
    if not isinstance(history, list):
        history = []
    event = dict(event)
    event.setdefault("ts", datetime.now(UTC).isoformat())
    history.append(event)
    write_json(path, history)
    return history


def main() -> None:
    root = lgwf_dir() / "prompt_acceptance"
    selection = read_json(root / "fix_selection.json", {})
    review = read_json(root / "repair_review.json", {})
    if not isinstance(selection, dict):
        selection = {}
    if not isinstance(review, dict):
        review = {}
    next_action = choose_next(selection, review)
    append_react_history(
        root,
        {
            "event": "prompt_repair_decided",
            "next": next_action,
            "passed": review.get("passed"),
            "remaining_issue_ids": review.get("remaining_issue_ids", []),
        },
    )
    print(json.dumps({"next": next_action}, ensure_ascii=False))


if __name__ == "__main__":
    main()
