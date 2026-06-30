from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, write_json


def build_review() -> dict:
    return {
        "passed": True,
        "skipped": True,
        "remaining_upgrade_ids": [],
        "summary": "没有已批准的 prompt 升级项，apply 阶段已跳过。",
    }


def main() -> None:
    review = build_review()
    write_json(lgwf_dir() / "prompt_upgrade" / "apply_review.json", review)
    output_state({"prompt_upgrade_apply_review": review, "prompt_upgrade_apply_skipped": True})


if __name__ == "__main__":
    main()
