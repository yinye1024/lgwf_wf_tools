from __future__ import annotations

import json
from pathlib import Path
from typing import Any


VALID_DELIVERY_ACTIONS = {"none", "stage", "commit"}


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else default


def load_runtime_input(root: Path = Path(".lgwf/checkpoints")) -> dict[str, Any]:
    if not root.exists():
        return {}
    checkpoints = sorted(root.glob("*/checkpoint.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in checkpoints:
        data = load_json(path, {})
        state = data.get("state_before_current_node", {})
        if isinstance(state, dict):
            nested = state.get("input")
            return nested if isinstance(nested, dict) else state
    return {}


def string_from_nested(payload: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    nested = payload.get("delivery_review_input")
    if isinstance(nested, dict):
        for key in keys:
            value = nested.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def load_review_context(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "delivery_review_input": {
                "final_change_brief_markdown": "# 变更摘要\n\n待补齐。\n",
                "commit_message_suggestion": "chore(git-diff-brief): summarize scoped git diff changes",
                "commit_message_suggestion_zh": "整理指定范围的 Git diff 摘要",
                "commit_message_rationale": "缺少 delivery_review_context.json，使用保守提交信息建议。",
                "commit_action_options": ["none", "stage", "commit"],
                "default_commit_action": "none",
                "open_delivery_questions": ["缺少 delivery_review_context.json，需补齐结果展示输出。"],
            }
        }
    return json.loads(path.read_text(encoding="utf-8"))


def load_markdown(path: Path) -> str:
    data = load_json(path, {})
    value = data.get("change_brief_markdown")
    if isinstance(value, str) and value.strip():
        return value if value.endswith("\n") else f"{value}\n"
    return "# 变更摘要\n\n待补齐。\n"


def build_delivery_review_input(
    review_context: dict[str, Any],
    summary_context: dict[str, Any],
    markdown: str,
) -> dict[str, Any]:
    raw_input = review_context.get("delivery_review_input")
    delivery_input = dict(raw_input) if isinstance(raw_input, dict) else dict(review_context)
    delivery_input["final_change_brief_markdown"] = string_from_nested(
        delivery_input, ["final_change_brief_markdown"]
    ) or markdown
    delivery_input["commit_message_suggestion"] = string_from_nested(
        delivery_input, ["commit_message_suggestion", "suggested_commit_message"]
    ) or string_from_nested(summary_context, ["commit_message_suggestion", "suggested_commit_message"])
    delivery_input["commit_message_suggestion_zh"] = string_from_nested(
        delivery_input, ["commit_message_suggestion_zh"]
    ) or string_from_nested(summary_context, ["commit_message_suggestion_zh"])
    delivery_input["commit_message_rationale"] = string_from_nested(
        delivery_input, ["commit_message_rationale", "commit_rationale"]
    ) or string_from_nested(summary_context, ["commit_message_rationale", "commit_rationale"])
    if not delivery_input["commit_message_suggestion"]:
        delivery_input["commit_message_suggestion"] = "chore(git-diff-brief): summarize scoped git diff changes"
    if not delivery_input["commit_message_rationale"]:
        delivery_input["commit_message_rationale"] = "摘要阶段未提供提交建议依据，使用保守默认值。"
    delivery_input["commit_action_options"] = ["none", "stage", "commit"]
    delivery_input["default_commit_action"] = "none"
    questions = delivery_input.get("open_delivery_questions")
    delivery_input["open_delivery_questions"] = questions if isinstance(questions, list) else []
    return delivery_input


def build_auto_delivery_decision(runtime_input: dict[str, Any], delivery_input: dict[str, Any]) -> dict[str, Any]:
    skip = bool(runtime_input.get("skip_delivery_review"))
    action = str(runtime_input.get("delivery_action", "none")).strip().lower() or "none"
    commit_message = str(runtime_input.get("commit_message", "")).strip()
    if not skip:
        return {"route": "review", "decision": None}
    if action not in VALID_DELIVERY_ACTIONS:
        return {
            "route": "skip",
            "decision": {
                "decision": "approve",
                "commit_action": action,
                "stage_scope": "target_scope",
                "commit_message": commit_message,
                "comment": "skip_delivery_review=true，但 delivery_action 不受支持，后续提交计划会失败。",
                "changes": [],
            },
        }
    if action == "commit" and not commit_message:
        commit_message = ""
    elif not commit_message:
        commit_message = str(delivery_input.get("commit_message_suggestion", "")).strip()
    return {
        "route": "skip",
        "decision": {
            "decision": "approve",
            "commit_action": action,
            "stage_scope": "target_scope",
            "commit_message": commit_message,
            "comment": "由 skip_delivery_review=true 自动生成最终交付决策。",
            "changes": [],
        },
    }


def main() -> None:
    review = load_review_context(Path(".lgwf/delivery_review_context.json"))
    summary = load_json(Path(".lgwf/change_summary_context.json"), {})
    markdown = load_markdown(Path(".lgwf/change_brief_markdown.json"))
    delivery_input = build_delivery_review_input(review, summary, markdown)
    auto_decision = build_auto_delivery_decision(load_runtime_input(), delivery_input)
    if isinstance(auto_decision.get("decision"), dict):
        Path(".lgwf/delivery_decision.json").write_text(
            json.dumps(auto_decision["decision"], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    payload = {
        "git_diff_brief.delivery_review_input": delivery_input,
        "__route__route_delivery_review": auto_decision["route"],
        "git_diff_brief.prepare_delivery_review_result": {
            "ok": True,
            "source_file": ".lgwf/delivery_review_context.json",
            "route": auto_decision["route"],
            "auto_decision_file": ".lgwf/delivery_decision.json" if auto_decision.get("decision") else "",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
