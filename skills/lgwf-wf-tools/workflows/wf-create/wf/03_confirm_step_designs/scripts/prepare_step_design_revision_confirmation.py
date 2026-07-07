"""根据 revise 决策构造步骤设计修订确认上下文。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from review_context import build_review_context


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def build_context(root: Path) -> dict:
    lgwf_dir = root / ".lgwf"
    proposal = load_json(lgwf_dir / "step_designs_proposal.json")
    revision_request = load_json(lgwf_dir / "step_design_confirmation_record.json")
    context = build_review_context(
        review_node="confirm_step_designs",
        title="确认修订后的步骤设计",
        approval_target="step_designs_revision",
        proposal=proposal,
        approve_writes=".lgwf/step_designs.json",
        persist_path=".lgwf/step_design_revision_approval.json",
        revision_request=revision_request,
    )
    context["revision_request"] = revision_request
    context["revision_persist"] = ".lgwf/step_design_revision_approval.json"
    context["instruction"] = (
        "请主 agent 根据 revision_request.changes 调整步骤设计对象；"
        "确认可继续时返回 decision=approve，并提供完整 JSON，不要只返回局部 diff。"
    )
    return context


def main() -> None:
    context = build_context(Path.cwd())
    print(json.dumps({"lgwf_wf_create.step_design_revision_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
