"""REVIEW 节点上下文生成工具。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


ALLOWED_REVIEW_DECISIONS = ["approve", "revise", "reject"]


def build_review_context(
    *,
    review_node: str,
    title: str,
    approval_target: str,
    proposal: dict[str, Any],
    approve_writes: str,
    persist_path: str,
    revision_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review_context_json: dict[str, Any] = {
        "review_node": review_node,
        "title": title,
        "approval_target": approval_target,
        "proposal": deepcopy(proposal),
        "allowed_decisions": list(ALLOWED_REVIEW_DECISIONS),
        "approve_writes": approve_writes,
        "persist_path": persist_path,
    }
    if revision_request is not None:
        review_context_json["revision_request"] = deepcopy(revision_request)

    return {
        "proposal": proposal,
        "approval_target": approval_target,
        "allowed_decisions": list(ALLOWED_REVIEW_DECISIONS),
        "approve_writes": approve_writes,
        "persist_path": persist_path,
        "review_reentry_node": review_node,
        "review_context_json": review_context_json,
        "display_template": (
            "**需要确认：{title}**\n\n"
            "- 当前状态：等待 REVIEW `{review_node}` 决策\n"
            "- 可选决策：`approve` / `revise` / `reject`\n"
            "- 待确认 JSON：完整展示 `review_context_json`\n"
            "- 提交值：按用户选择提交完整 JSON decision record"
        ),
        "revise_instruction": (
            "当用户要求调整时，主 agent 必须结合用户修改需求返回完整 JSON；"
            "保留 review_context_json.proposal 的完整业务对象，写明 changes/comment，"
            "并让 workflow 重新进入同一个 REVIEW 节点。"
        ),
    }
