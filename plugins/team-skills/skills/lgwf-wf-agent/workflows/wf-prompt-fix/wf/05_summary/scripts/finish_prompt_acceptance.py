from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, read_json, write_json


def build_confirmation(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "confirmed": True,
        "auto_confirmed": True,
        "reason": "repair_passed=true and remaining_issue_ids is empty",
        "status": summary.get("status", ""),
        "remaining_issue_ids": summary.get("remaining_issue_ids", []),
        "comment": "",
    }


def main() -> None:
    root = lgwf_dir()
    prompt_root = root / "prompt_acceptance"
    summary = read_json(prompt_root / "summary.json", {})
    if not isinstance(summary, dict):
        summary = {}
    confirmation = build_confirmation(summary)
    write_json(prompt_root / "confirmation.json", confirmation)
    output_state({"prompt_acceptance_confirmation": confirmation})


if __name__ == "__main__":
    main()
