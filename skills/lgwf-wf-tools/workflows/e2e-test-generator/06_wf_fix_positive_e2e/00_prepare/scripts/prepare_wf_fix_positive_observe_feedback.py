from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    observe_path = Path(".lgwf/e2e_wf_fix_positive_observe.json")
    observe_path.parent.mkdir(parents=True, exist_ok=True)
    real_positive_design_path = Path(".lgwf/e2e_real_positive_design.json")
    if not real_positive_design_path.exists():
        real_positive_design_path.write_text(
            json.dumps(
                {
                    "source_missing": True,
                    "summary": "本次未生成普通 real_positive 设计；wf_fix_positive 阶段必须基于 workflow graph 和业务摘要构造等价固定正向场景。",
                    "design_warnings": [
                        "缺少 .lgwf/e2e_real_positive_design.json，不能假设已有普通真实正向场景。"
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if not observe_path.exists():
        observe_path.write_text(
            json.dumps(
                {
                    "passed": False,
                    "issues": [],
                    "summary": "首轮默认 observe 占位文件；等待 OBSERVE 阶段写入真实验收结果。",
                    "commands": [],
                    "criterion_checks": {},
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
