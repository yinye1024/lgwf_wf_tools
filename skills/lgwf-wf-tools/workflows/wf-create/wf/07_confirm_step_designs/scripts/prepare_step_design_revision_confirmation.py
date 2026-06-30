"""根据 revise 决策构造步骤设计修订确认上下文。"""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def build_context(root: Path) -> dict:
    lgwf_dir = root / ".lgwf"
    return {
        "proposal": load_json(lgwf_dir / "step_designs_proposal.json"),
        "revision_request": load_json(lgwf_dir / "step_design_confirmation_record.json"),
        "approval_target": "step_designs_revision",
        "allowed_decisions": ["approve", "revise", "reject"],
        "approve_writes": ".lgwf/step_designs.json",
        "revision_persist": ".lgwf/step_design_revision_approval.json",
        "instruction": "请主 agent 根据 revision_request.changes 调整步骤设计对象；确认可继续时返回 decision=approve 和 confirmed。"
    }


def main() -> None:
    context = build_context(Path.cwd())
    print(json.dumps({"lgwf_wf_create.step_design_revision_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
