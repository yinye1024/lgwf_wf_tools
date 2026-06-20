from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import lgwf_dir, output_state, read_json, write_json


def build_context(audit: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    return {
        "artifact_root": ".lgwf/prompt_acceptance",
        "audit_passed": bool(audit.get("passed")) and not issues,
        "prompt_count": len(inventory.get("prompts", [])) if isinstance(inventory.get("prompts"), list) else 0,
        "issues": issues,
        "instructions": {
            "fix_all": "Set true to repair every listed prompt issue.",
            "selected_issue_ids": "Provide a list of issue ids to repair.",
            "skip_fix": "Set true to skip prompt repair and continue.",
            "comment": "Optional operator note.",
        },
    }


def main() -> None:
    root = lgwf_dir() / "prompt_acceptance"
    audit = read_json(root / "audit.json", {})
    inventory = read_json(root / "inventory.json", {})
    if not isinstance(audit, dict):
        audit = {}
    if not isinstance(inventory, dict):
        inventory = {}
    context = build_context(audit, inventory)
    write_json(root / "selection_context.json", context)
    if not (root / "react_history.json").exists():
        write_json(root / "react_history.json", [])
    if not (root / "repair_review.json").exists():
        write_json(root / "repair_review.json", {"passed": False, "remaining_issue_ids": []})
    output_state({"prompt_fix_selection_context": context})


if __name__ == "__main__":
    main()
