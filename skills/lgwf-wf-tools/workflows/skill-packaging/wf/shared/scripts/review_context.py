"""构造固定三选项 REVIEW 上下文。"""

from __future__ import annotations

from typing import Any


def build_review_context(
    *,
    title: str,
    review_node: str,
    approval_target: str,
    approve_writes: str,
    persist_path: str,
    proposal: dict[str, Any],
    revise_instruction: str,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    review_context_json = {
        "review_node": review_node,
        "approval_target": approval_target,
        "approve_writes": approve_writes,
        "persist_path": persist_path,
        "allowed_decisions": ["approve", "revise", "reject"],
        "proposal": proposal,
    }
    return {
        "title": title,
        "review_node": review_node,
        "approval_target": approval_target,
        "approve_writes": approve_writes,
        "persist_path": persist_path,
        "allowed_decisions": ["approve", "revise", "reject"],
        "proposal": proposal,
        "review_context_json": review_context_json,
        "revise_instruction": revise_instruction,
        "notes": list(notes or []),
    }
