from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    observe_path = Path(".lgwf/e2e_real_positive_observe.json")
    observe_path.parent.mkdir(parents=True, exist_ok=True)
    if not observe_path.exists():
        observe_path.write_text(
            json.dumps(
                {
                    "passed": False,
                    "issues": [],
                    "summary": "首轮默认 observe 占位文件；等待 OBSERVE 阶段写入真实验收结果。",
                    "commands": [],
                    "contract_checks": {},
                    "scenario_checks": {},
                    "coverage_gaps": [],
                    "initial_placeholder": True,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"prepared": True, "path": str(observe_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
