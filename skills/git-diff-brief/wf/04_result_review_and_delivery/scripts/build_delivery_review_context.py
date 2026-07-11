from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else default


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def clean_markdown(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value if value.endswith("\n") else f"{value}\n"
    return "# 变更摘要\n\n未找到可交付的 Markdown 草稿。\n"


def format_key_files(items: list[Any]) -> list[str]:
    result: list[str] = []
    for item in items:
        if isinstance(item, dict):
            path = str(item.get("path") or item.get("file") or "").strip()
            summary = str(item.get("summary") or item.get("description") or "").strip()
            if path and summary:
                result.append(f"{path}：{summary}")
            elif path or summary:
                result.append(path or summary)
        else:
            text = str(item).strip()
            if text:
                result.append(text)
    return result


def format_risks(items: list[Any]) -> list[str]:
    result: list[str] = []
    for item in items:
        if isinstance(item, dict):
            level = str(item.get("level") or "").strip()
            point = str(item.get("point") or item.get("summary") or "").strip()
            if level and point:
                result.append(f"{level}：{point}")
            elif point:
                result.append(point)
        else:
            text = str(item).strip()
            if text:
                result.append(text)
    return result


def format_validation(items: list[Any]) -> list[str]:
    result: list[str] = []
    for item in items:
        if isinstance(item, dict):
            command = str(item.get("command") or "").strip()
            purpose = str(item.get("purpose") or "").strip()
            if command and purpose:
                result.append(f"{command}（{purpose}）")
            elif command:
                result.append(command)
        else:
            text = str(item).strip()
            if text:
                result.append(text)
    return result


def main() -> None:
    lgwf_dir = Path(".lgwf")
    brief = load_json(lgwf_dir / "change_brief_markdown.json", {})
    summary = load_json(lgwf_dir / "change_summary_context.json", {})
    git_context = load_json(lgwf_dir / "git_context_snapshot.json", {})

    markdown = clean_markdown(brief.get("change_brief_markdown"))
    support = summary.get("summary_supporting_context")
    support = support if isinstance(support, dict) else {}
    git_log = git_context.get("git_collection_log")
    git_log = git_log if isinstance(git_log, dict) else {}
    changed_index = git_context.get("changed_files_index")
    changed_index = changed_index if isinstance(changed_index, dict) else {}

    repo_path = str(git_log.get("requested_repo_path") or git_log.get("repo_path") or support.get("repo_path") or "").strip()
    relative_scope = str(git_log.get("relative_scope") or support.get("relative_scope") or "").strip()
    changed_files_count = changed_index.get("count") or support.get("changed_files_index_count") or ""

    commit_message = str(summary.get("commit_message_suggestion") or "").strip()
    commit_message_zh = str(summary.get("commit_message_suggestion_zh") or "").strip()
    commit_rationale = str(summary.get("commit_message_rationale") or "").strip()
    if not commit_message:
        commit_message = "chore(git-diff-brief): summarize repository changes"
    if not commit_message_zh:
        commit_message_zh = "chore(git-diff-brief): 汇总仓库变更"
    if not commit_rationale:
        commit_rationale = "基于已生成摘要上下文给出保守提交信息建议。"

    validation = format_validation(as_list(summary.get("validation_candidates")))
    delivery_input = {
        "repo_path": repo_path,
        "relative_scope": relative_scope,
        "changed_files_count": changed_files_count,
        "final_change_brief_markdown": markdown,
        "change_overview": as_list(summary.get("change_overview")),
        "key_files": format_key_files(as_list(summary.get("key_files"))),
        "risk_points": format_risks(as_list(summary.get("risk_points"))),
        "validation_candidates": validation,
        "summary_supporting_context": support,
        "commit_message_suggestion": commit_message,
        "commit_message_suggestion_zh": commit_message_zh,
        "commit_message_rationale": commit_rationale,
        "commit_action_options": ["none", "stage", "commit"],
        "default_commit_action": "none",
        "open_delivery_questions": [
            "是否接受当前摘要，还是需要先补齐 compact diff 被裁剪的内容。",
            "是否需要把当前 Markdown 默认落盘；如果需要，文件命名策略是什么。",
            "如果选择 revise，应原地重写当前草稿，还是保留多版本索引。",
            "本次人工确认是否保持 commit_action=none，还是显式选择 stage 或 commit。",
            "当前 relative_scope 为空字符串，表示仓库根目录；如需 stage 或 commit，必须额外确认根目录写操作。",
        ],
    }
    payload = {
        "delivery_review_input": delivery_input,
        "final_change_brief_markdown": markdown,
        "summary_supporting_context": support,
        "commit_message_suggestion": commit_message,
        "commit_message_suggestion_zh": commit_message_zh,
        "commit_message_rationale": commit_rationale,
        "commit_action_options": ["none", "stage", "commit"],
        "default_commit_action": "none",
        "open_delivery_questions": delivery_input["open_delivery_questions"],
    }
    output_path = lgwf_dir / "delivery_review_context.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "git_diff_brief.delivery_review_context_result": {
                    "ok": True,
                    "source": ".lgwf/change_brief_markdown.json",
                    "output": ".lgwf/delivery_review_context.json",
                }
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
