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


def list_from_nested(payload: dict[str, Any], keys: list[str]) -> list[Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
    nested = payload.get("delivery_review_input")
    if isinstance(nested, dict):
        for key in keys:
            value = nested.get(key)
            if isinstance(value, list):
                return value
    return []


def dict_from_nested(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    nested = payload.get("delivery_review_input")
    if isinstance(nested, dict):
        for key in keys:
            value = nested.get(key)
            if isinstance(value, dict):
                return value
    return {}


def value_from_nested(payload: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return value
    nested = payload.get("delivery_review_input")
    if isinstance(nested, dict):
        for key in keys:
            value = nested.get(key)
            if value not in (None, ""):
                return value
    return None


def format_list(items: list[Any], fallback: str, limit: int | None = None) -> str:
    cleaned: list[str] = []
    for item in items:
        if isinstance(item, dict):
            path = str(item.get("path") or item.get("file") or item.get("name") or "").strip()
            note = str(item.get("summary") or item.get("description") or item.get("reason") or "").strip()
            text = f"{path}：{note}" if path and note else path or note
        else:
            text = str(item).strip()
        if text:
            cleaned.append(text)
    selected = cleaned[:limit] if limit else cleaned
    if not selected:
        selected = [fallback]
    return "\n".join(f"- {item}" for item in selected)


def build_selection_prompt(delivery_input: dict[str, Any], summary_context: dict[str, Any]) -> str:
    supporting_context = dict_from_nested(delivery_input, ["summary_supporting_context"])
    if not supporting_context:
        supporting_context = dict_from_nested(summary_context, ["summary_supporting_context"])
    git_log = dict_from_nested(supporting_context, ["git_collection_log"])
    changed_files = dict_from_nested(supporting_context, ["changed_files_index"])
    repo_path = (
        string_from_nested(delivery_input, ["repo_path", "scoped_repo_path", "target_repo"])
        or str(git_log.get("requested_repo_path") or git_log.get("repo_path") or "未生成该部分").strip()
    )
    relative_scope = str(git_log.get("relative_scope", "")).strip()
    if repo_path != "未生成该部分" and relative_scope:
        repo_path = f"{repo_path} ({relative_scope})"
    changed_count = (
        value_from_nested(delivery_input, ["changed_files_path_entries", "summarized_file_count"])
        or changed_files.get("count")
        or supporting_context.get("changed_files_path_entries")
        or supporting_context.get("summarized_file_count")
        or value_from_nested(delivery_input, ["changed_files_count"])
        or supporting_context.get("changed_files_count")
        or "未生成该部分"
    )
    overview = list_from_nested(delivery_input, ["change_overview"]) or list_from_nested(summary_context, ["change_overview"])
    key_files = list_from_nested(delivery_input, ["key_files"]) or list_from_nested(summary_context, ["key_files"])
    risks = list_from_nested(delivery_input, ["risk_points"]) or list_from_nested(summary_context, ["risk_points"])
    validations = (
        list_from_nested(delivery_input, ["validation_candidates", "validation_suggestions"])
        or list_from_nested(summary_context, ["validation_candidates", "validation_suggestions"])
        or list_from_nested(supporting_context, ["validation_candidates", "validation_suggestions", "suggested_verification_commands"])
    )
    commit_message = str(delivery_input.get("commit_message_suggestion", "")).strip()
    commit_message_zh = str(delivery_input.get("commit_message_suggestion_zh", "")).strip() or "未生成该部分"
    rationale = str(delivery_input.get("commit_message_rationale", "")).strip() or "未生成该部分"
    return f"""本次变更摘要预览：

目标仓库：{repo_path}
变更文件数：{changed_count}

变更概览：
{format_list(overview, "未生成该部分", limit=3)}

关键文件：
{format_list(key_files, "未生成该部分", limit=5)}

风险点：
{format_list(risks, "未生成该部分", limit=2)}

建议验证命令：
{format_list(validations, "未生成该部分")}

建议 commit message（英文，默认用于 git commit -m）：
{commit_message or "未生成该部分"}

建议 commit message（中文，用于理解）：
{commit_message_zh}

理由：
{rationale}

请选择本次最终交付动作：

1. 接受摘要
   结束 workflow，不执行 git add 或 git commit。

2. 接受摘要，并执行 git add
   对当前确认范围执行 git add，不创建 commit。

3. 接受摘要，执行 git add，并创建 commit
   使用建议 commit message 创建 commit：
   {commit_message or "未生成该部分"}

4. 返回修订摘要
   不继续交付，请说明需要修改哪些摘要内容。

5. 拒绝并终止 workflow
   结束本次 run，不接受当前摘要。

请回复 1、2、3、4 或 5。"""


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
    runtime_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_input = review_context.get("delivery_review_input")
    delivery_input = dict(raw_input) if isinstance(raw_input, dict) else dict(review_context)
    runtime_input = runtime_input or {}
    if not string_from_nested(delivery_input, ["repo_path", "scoped_repo_path", "target_repo"]):
        repo_path = string_from_nested(runtime_input, ["repo_path", "target_repo", "repository"])
        if repo_path:
            delivery_input["repo_path"] = repo_path
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
    delivery_input["selection_prompt"] = build_selection_prompt(delivery_input, summary_context)
    return delivery_input


def build_auto_delivery_decision(runtime_input: dict[str, Any], delivery_input: dict[str, Any]) -> dict[str, Any]:
    skip = bool(runtime_input.get("skip_delivery_review"))
    action = str(runtime_input.get("delivery_action", "none")).strip().lower() or "none"
    commit_message = str(runtime_input.get("commit_message", "")).strip()
    if not skip:
        return {"route": "review", "decision": None}
    if action not in VALID_DELIVERY_ACTIONS:
        delivery_input["open_delivery_questions"].append(
            f"skip_delivery_review=true，但 delivery_action={action!r} 不受支持，必须进入人工确认重新选择。"
        )
        return {
            "route": "review",
            "decision": None,
        }
    if action in {"stage", "commit"}:
        delivery_input["open_delivery_questions"].append(
            f"skip_delivery_review=true 且 delivery_action={action} 涉及 Git 写操作，必须进入人工确认。"
        )
        return {"route": "review", "decision": None}
    if not commit_message:
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
    runtime_input = load_runtime_input()
    delivery_input = build_delivery_review_input(review, summary, markdown, runtime_input)
    auto_decision = build_auto_delivery_decision(runtime_input, delivery_input)
    decision = auto_decision.get("decision")
    if not isinstance(decision, dict):
        decision = {
            "decision": "pending_review",
            "commit_action": "none",
            "stage_scope": "target_scope",
            "commit_message": str(delivery_input.get("commit_message_suggestion", "")).strip(),
            "comment": "等待人工确认；此占位决策应由 REVIEW 节点覆盖。",
            "changes": [],
        }
    Path(".lgwf/delivery_decision.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2),
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
            "decision_file": ".lgwf/delivery_decision.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
