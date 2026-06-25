from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, read_json, write_json


_UNTRACKED_VCS_MARKERS = (
    "untracked in git",
    "untracked target package",
    "target package is untracked",
    "cannot be proven absent with VCS evidence",
    "cannot be enumerated from VCS",
    "无法用 Git 证明",
    "未被 Git 跟踪",
    "缺少 VCS 基线",
)


def _text_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _only_untracked_vcs_evidence_gap(review: dict[str, Any]) -> bool:
    """Treat legacy observe output for a new untracked package as non-blocking."""
    if review.get("remaining_upgrade_ids"):
        return False
    if review.get("missing_changes"):
        return False

    step_results = review.get("step_results")
    if isinstance(step_results, list):
        for step in step_results:
            if isinstance(step, dict) and step.get("passed") is False:
                return False

    issues = _text_items(review.get("issues"))
    unexpected_changes = _text_items(review.get("unexpected_changes"))
    blockers = [*issues, *unexpected_changes]
    if not blockers:
        return False

    return all(
        any(marker in item for marker in _UNTRACKED_VCS_MARKERS)
        for item in blockers
    )


def choose_next(review: dict[str, Any]) -> str:
    if review.get("passed") is True and not review.get("remaining_upgrade_ids"):
        return "exit"
    if _only_untracked_vcs_evidence_gap(review):
        return "exit"
    return "continue"


def append_history(root: Path, event: dict[str, Any]) -> None:
    path = root / "react_history.json"
    history = read_json(path, [])
    if not isinstance(history, list):
        history = []
    event = dict(event)
    event.setdefault("ts", datetime.now(UTC).isoformat())
    history.append(event)
    write_json(path, history)


def main() -> None:
    root = lgwf_dir() / "prompt_upgrade"
    review = read_json(root / "apply_review.json", {})
    if not isinstance(review, dict):
        review = {}
    next_action = choose_next(review)
    append_history(
        root,
        {
            "event": "prompt_upgrade_apply_decided",
            "next": next_action,
            "passed": review.get("passed"),
            "treated_untracked_vcs_gap_as_warning": _only_untracked_vcs_evidence_gap(review),
            "remaining_upgrade_ids": review.get("remaining_upgrade_ids", []),
        },
    )
    print(json.dumps({"next": next_action}, ensure_ascii=False))


if __name__ == "__main__":
    main()
