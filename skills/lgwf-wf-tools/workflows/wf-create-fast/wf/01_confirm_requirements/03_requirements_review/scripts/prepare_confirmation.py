"""根据需求 proposal 构造 approval 可读上下文。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from review_context import build_review_context


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def build_context(root: Path) -> dict:
    proposal = load_json(root / ".lgwf" / "create_requirements_proposal.json")
    return build_review_context(
        review_node="confirm_requirements",
        title="确认需求方案",
        approval_target="create_requirements_proposal",
        proposal=proposal,
        approve_writes=".lgwf/create_requirements.json",
        persist_path=".lgwf/create_requirements_approval.json",
    )


def main() -> None:
    context = build_context(Path.cwd())
    print(json.dumps({"lgwf_wf_create_fast.requirements_confirmation_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
