"""根据业务流转 proposal 构造 approval 可读上下文。"""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def build_context(root: Path) -> dict:
    proposal = load_json(root / ".lgwf" / "business_flow_proposal.json")
    return {
        "proposal": proposal,
        "approval_target": "business_flow_proposal",
        "allowed_decisions": ["approve", "reject"],
        "approve_writes": ".lgwf/business_flow.json",
        "revise_or_reject_route": "summarize_create_result",
    }


def main() -> None:
    context = build_context(Path.cwd())
    print(json.dumps({"lgwf_wf_create.business_flow_confirmation_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
