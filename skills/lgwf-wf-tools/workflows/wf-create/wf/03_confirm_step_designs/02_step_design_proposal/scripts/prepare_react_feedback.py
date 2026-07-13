"""初始化步骤设计 proposal ReAct 的空反馈文件。"""

from __future__ import annotations

import json
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    write_json(lgwf_dir / "step_designs_proposal_quality_gate.json", {})
    write_json(lgwf_dir / "step_designs_proposal_decision.json", {})
    print(
        json.dumps(
            {
                "prepared": True,
                "files": [
                    ".lgwf/step_designs_proposal_quality_gate.json",
                    ".lgwf/step_designs_proposal_decision.json",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
