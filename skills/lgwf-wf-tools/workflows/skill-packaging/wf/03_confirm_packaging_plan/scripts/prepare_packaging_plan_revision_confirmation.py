"""根据 revise 决策重建打包计划确认上下文。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from confirmation_io import unwrap_approval
from packaging_common import load_lgwf_artifact, write_json
from review_context import build_review_context


def main() -> None:
    root = Path.cwd()
    approval = unwrap_approval(
        load_lgwf_artifact(root, "packaging_plan_approval.json"),
        "packaging_plan_approval",
    )
    if approval["approval"] != "revise":
        raise ValueError("只有 revise 才能重建打包计划确认上下文")

    proposal = load_lgwf_artifact(root, "packaging_plan_proposal.json")
    context = build_review_context(
        title="确认打包计划",
        review_node="confirm_packaging_plan",
        approval_target="packaging_plan_proposal",
        approve_writes=".lgwf/confirmed_packaging_plan.json",
        persist_path=".lgwf/packaging_plan_approval.json",
        proposal=proposal,
        revise_instruction="revise 必须提交完整 JSON 决策记录，并明确指出需要调整的计划项或风险项。",
        notes=[
            "当前 workflow 不自动修复失败，也不自动修改 facade registry。",
            "如果目标目录已存在，approve 表示显式接受覆盖风险。",
            f"上一轮 revise 原始记录：{json.dumps(approval, ensure_ascii=False)}",
        ],
    )
    context["latest_revision_request"] = approval
    write_json(root / ".lgwf" / "packaging_plan_confirmation_context.json", context)
    print(
        json.dumps(
            {"skill_packaging.packaging_plan_confirmation_context": context},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

