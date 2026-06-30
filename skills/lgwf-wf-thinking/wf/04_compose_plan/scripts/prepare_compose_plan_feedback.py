from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    path = Path.cwd() / ".lgwf" / "composition_plan_observe.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "passed": False,
                    "issues": [],
                    "summary": "首轮默认 observe 占位文件；等待 OBSERVE 阶段写入真实验收结果。",
                    "initial_placeholder": True,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"lgwf_wf_thinking.compose_feedback_prepared": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
