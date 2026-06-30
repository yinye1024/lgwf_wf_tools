from __future__ import annotations

from pathlib import Path
import json


def main() -> None:
    path = Path(".lgwf/e2e_runtime_fake_repair_context.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(
                {
                    "active": False,
                    "attempt": 0,
                    "blockers": [],
                    "issue_signature": "",
                    "previous_signatures": [],
                    "no_progress": False,
                    "instructions": [
                        "首轮生成没有上一轮 observe 结果；按设计契约生成 runtime fake E2E。",
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    observe_path = Path(".lgwf/e2e_runtime_fake_observe.json")
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
    print(json.dumps({"prepared": True, "path": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
