from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import lgwf_dir, output_state, read_json, write_json


def build_summary(
    *,
    inventory: dict[str, Any],
    audit: dict[str, Any],
    selection: dict[str, Any],
    review: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    prompts = inventory.get("prompts") if isinstance(inventory.get("prompts"), list) else []
    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    selected = selection.get("selected_issue_ids") if isinstance(selection.get("selected_issue_ids"), list) else []
    if not issues:
        status = "passed"
    elif selection.get("skip_fix"):
        status = "skipped"
    elif review.get("passed") is True and not review.get("remaining_issue_ids"):
        status = "fixed"
    else:
        status = "needs_attention"
    return {
        "status": status,
        "artifact_root": ".lgwf/prompt_acceptance",
        "root_summary_path": ".lgwf/target_prompt_acceptance_summary.json",
        "prompt_count": len(prompts),
        "issue_count": len(issues),
        "selected_issue_ids": selected,
        "remaining_issue_ids": review.get("remaining_issue_ids", []),
        "audit_passed": bool(audit.get("passed")) and not issues,
        "repair_passed": review.get("passed"),
        "summary": review.get("summary") or audit.get("summary") or "",
        "history": history,
    }


def main() -> None:
    root = lgwf_dir()
    prompt_root = root / "prompt_acceptance"
    inventory = read_json(prompt_root / "inventory.json", {})
    audit = read_json(prompt_root / "audit.json", {})
    selection = read_json(prompt_root / "fix_selection.json", {})
    review = read_json(prompt_root / "repair_review.json", {})
    history = read_json(prompt_root / "react_history.json", [])
    if not isinstance(inventory, dict):
        inventory = {}
    if not isinstance(audit, dict):
        audit = {}
    if not isinstance(selection, dict):
        selection = {}
    if not isinstance(review, dict):
        review = {}
    if not isinstance(history, list):
        history = []
    summary = build_summary(inventory=inventory, audit=audit, selection=selection, review=review, history=history)
    write_json(root / "target_prompt_acceptance_summary.json", summary)
    write_json(prompt_root / "summary.json", summary)
    output_state({"prompt_acceptance_summary": summary})


if __name__ == "__main__":
    main()
