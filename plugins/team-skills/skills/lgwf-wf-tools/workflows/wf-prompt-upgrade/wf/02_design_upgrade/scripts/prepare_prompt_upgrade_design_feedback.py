from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_upgrade_common import lgwf_dir, output_state, write_json


def main() -> None:
    path = lgwf_dir() / "prompt_upgrade" / "proposal_review.json"
    if not path.exists():
        write_json(
            path,
            {
                "passed": False,
                "issues": [],
                "summary": "首轮默认 observe 占位文件；等待 OBSERVE 阶段写入真实验收结果。",
                "initial_placeholder": True,
            },
        )
    output_state({"design_feedback_prepared": True})


if __name__ == "__main__":
    main()
