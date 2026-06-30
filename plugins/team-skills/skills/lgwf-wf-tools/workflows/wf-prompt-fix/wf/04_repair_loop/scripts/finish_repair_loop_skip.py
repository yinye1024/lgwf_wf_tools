from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, write_json


def build_review() -> dict:
    return {
        "passed": False,
        "skipped": True,
        "remaining_issue_ids": [],
        "summary": "用户未选择需要自动修复的 prompt issue，repair_loop 已跳过。",
    }


def main() -> None:
    review = build_review()
    write_json(lgwf_dir() / "prompt_acceptance" / "repair_review.json", review)
    output_state({"prompt_repair_review": review, "prompt_repair_skipped": True})


if __name__ == "__main__":
    main()
