"""根据需求 proposal 构造 approval 可读上下文。"""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def build_context(root: Path) -> dict:
    proposal = load_json(root / ".lgwf" / "create_requirements_proposal.json")
    return {
        "proposal": proposal,
        "approval_target": "create_requirements_proposal",
        "allowed_decisions": ["approve", "revise", "reject"],
        "approve_writes": ".lgwf/create_requirements.json",
        "revise_or_reject_route": "summarize_create_result",
    }


def main() -> None:
    context = build_context(Path.cwd())
    print(json.dumps({"lgwf_wf_create.requirements_confirmation_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
