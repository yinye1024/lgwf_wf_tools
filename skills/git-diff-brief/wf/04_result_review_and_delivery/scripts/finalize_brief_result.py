from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else default


def load_markdown(lgwf_dir: Path) -> str:
    brief = load_json(lgwf_dir / "change_brief_markdown.json", {})
    if isinstance(brief.get("change_brief_markdown"), str):
        return str(brief["change_brief_markdown"])

    review = load_json(lgwf_dir / "delivery_review_context.json", {})
    if isinstance(review.get("final_change_brief_markdown"), str):
        return str(review["final_change_brief_markdown"])
    delivery_input = review.get("delivery_review_input")
    if isinstance(delivery_input, dict) and isinstance(delivery_input.get("final_change_brief_markdown"), str):
        return str(delivery_input["final_change_brief_markdown"])
    return "# 变更摘要\n\n未找到可交付的 Markdown 草稿。\n"


def load_delivery_decision(lgwf_dir: Path) -> dict[str, Any]:
    decision = load_json(lgwf_dir / "delivery_decision.json", {})
    value = decision.get("value")
    return value if isinstance(value, dict) else decision


def load_git_context(lgwf_dir: Path) -> dict[str, Any]:
    return load_json(lgwf_dir / "git_context_snapshot.json", {})


def load_summary_context(lgwf_dir: Path) -> dict[str, Any]:
    return load_json(lgwf_dir / "change_summary_context.json", {})


def load_review_context(lgwf_dir: Path) -> dict[str, Any]:
    return load_json(lgwf_dir / "delivery_review_context.json", {})


def _string_from_nested(payload: dict[str, Any], keys: list[str]) -> str:
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


def resolve_confirmed_delivery_action(review_context: dict[str, Any]) -> dict[str, Any]:
    action = _string_from_nested(review_context, ["confirmed_commit_action", "selected_commit_action"])
    message = _string_from_nested(review_context, ["confirmed_commit_message", "selected_commit_message"])
    allow_root = bool(
        review_context.get("confirmed_allow_repo_root_write")
        or review_context.get("selected_allow_repo_root_write")
    )
    return {
        "commit_action": action,
        "commit_message": message,
        "allow_repo_root_write": allow_root,
    }


def resolve_commit_message_suggestion(
    review_context: dict[str, Any],
    summary_context: dict[str, Any],
    git_context: dict[str, Any],
) -> dict[str, str]:
    message = _string_from_nested(review_context, ["commit_message_suggestion", "suggested_commit_message"])
    message_zh = _string_from_nested(review_context, ["commit_message_suggestion_zh"])
    rationale = _string_from_nested(review_context, ["commit_message_rationale", "commit_rationale"])
    if not message:
        message = _string_from_nested(summary_context, ["commit_message_suggestion", "suggested_commit_message"])
    if not message_zh:
        message_zh = _string_from_nested(summary_context, ["commit_message_suggestion_zh"])
    if not rationale:
        rationale = _string_from_nested(summary_context, ["commit_message_rationale", "commit_rationale"])
    if message:
        return {
            "message": message,
            "message_zh": message_zh,
            "rationale": rationale or "来自摘要阶段生成的建议提交信息。",
        }

    log = git_context.get("git_collection_log", {})
    relative_scope = ""
    if isinstance(log, dict):
        relative_scope = str(log.get("relative_scope", "")).strip("/")
    scope_name = Path(relative_scope).name if relative_scope else "repo"
    fallback = f"chore({scope_name}): summarize scoped git diff changes"
    return {
        "message": fallback,
        "message_zh": "",
        "rationale": f"未发现摘要阶段提交建议，按当前 Git 作用域 `{relative_scope or '.'}` 生成保守 Conventional Commit。",
    }


def normalize_delivery_decision(
    decision: dict[str, Any],
    commit_message_suggestion: str = "",
    default_commit_action: str = "none",
    default_commit_message: str = "",
    default_allow_repo_root_write: bool = False,
) -> dict[str, Any]:
    decision_value = decision.get("decision", decision.get("approval", ""))
    changes = decision.get("changes", [])
    action = str(decision.get("commit_action") or default_commit_action or "none").strip().lower() or "none"
    return {
        "decision": str(decision_value).strip().lower() or "approve",
        "comment": str(decision.get("comment", "")).strip(),
        "changes": changes if isinstance(changes, list) else [],
        "commit_action": action,
        "stage_scope": str(decision.get("stage_scope", "target_scope")).strip() or "target_scope",
        "commit_message": str(
            decision.get("commit_message", "") or default_commit_message or commit_message_suggestion
        ).strip(),
        "allow_repo_root_write": bool(decision.get("allow_repo_root_write") or default_allow_repo_root_write),
    }


def build_commit_plan(decision: dict[str, Any], git_context: dict[str, Any]) -> dict[str, Any]:
    action = str(decision.get("commit_action", "none")).strip().lower() or "none"
    def invalid_plan(error: str) -> dict[str, Any]:
        return {
            "ok": False,
            "action": action,
            "executed": False,
            "commands": [],
            "error": error,
            "repo_path": "",
            "relative_scope": "",
            "scope_display": "",
            "requires_repo_root_confirmation": False,
            "commit_message": str(decision.get("commit_message", "")).strip(),
        }

    if action == "none":
        return {
            "ok": True,
            "action": "none",
            "executed": False,
            "commands": [],
            "repo_path": "",
            "relative_scope": "",
            "scope_display": "",
            "requires_repo_root_confirmation": False,
            "commit_message": str(decision.get("commit_message", "")).strip(),
        }
    if action not in {"stage", "commit"}:
        return invalid_plan("commit_action 不受支持。")
    if str(decision.get("stage_scope", "target_scope")).strip() != "target_scope":
        return invalid_plan("stage_scope 只能是 target_scope。")
    if action == "commit" and not str(decision.get("commit_message", "")).strip():
        return invalid_plan("commit_action=commit 需要非空 commit_message。")

    log = git_context.get("git_collection_log", {})
    if not isinstance(log, dict):
        return invalid_plan("缺少 git_collection_log。")
    repo_path = str(log.get("repo_path", "")).strip()
    if "relative_scope" not in log:
        return invalid_plan("缺少 relative_scope。")
    relative_scope = str(log.get("relative_scope", "")).strip().strip("/")
    if not repo_path:
        return invalid_plan("缺少 repo_path。")

    requires_repo_root_confirmation = not relative_scope
    scope_arg = relative_scope or "."
    if requires_repo_root_confirmation and not bool(decision.get("allow_repo_root_write")):
        plan = invalid_plan("目标作用域是仓库根目录；执行 stage/commit 必须显式设置 allow_repo_root_write=true。")
        plan["repo_path"] = repo_path
        plan["relative_scope"] = "."
        plan["scope_display"] = "."
        plan["requires_repo_root_confirmation"] = True
        return plan
    commands = [["git", "add", "--all", "--", scope_arg]]
    if action == "commit":
        commands.append(["git", "commit", "-m", str(decision.get("commit_message", "")).strip()])
    return {
        "ok": True,
        "action": action,
        "executed": True,
        "commands": commands,
        "repo_path": repo_path,
        "relative_scope": scope_arg,
        "scope_display": scope_arg,
        "requires_repo_root_confirmation": requires_repo_root_confirmation,
        "commit_message": str(decision.get("commit_message", "")).strip(),
    }


def execute_commit_action(plan: dict[str, Any]) -> dict[str, Any]:
    if not plan.get("ok"):
        return {
            "ok": False,
            "action": plan.get("action", ""),
            "executed": False,
            "commands": plan.get("commands", []),
            "error": plan.get("error", "commit plan 无效。"),
        }
    commands = plan.get("commands", [])
    if not commands:
        return {
            "ok": True,
            "action": plan.get("action", "none"),
            "executed": False,
            "commands": [],
            "stdout": "",
            "stderr": "",
        }

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    command_records: list[list[str]] = []
    for command in commands:
        command_records.append([str(item) for item in command])
        completed = subprocess.run(
            command,
            cwd=str(plan.get("repo_path", "")),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout_parts.append(completed.stdout or "")
        stderr_parts.append(completed.stderr or "")
        if completed.returncode != 0:
            return {
                "ok": False,
                "action": plan.get("action", ""),
                "executed": True,
                "commands": command_records,
                "exit_code": completed.returncode,
                "stdout": "".join(stdout_parts),
                "stderr": "".join(stderr_parts),
                "error": "Git 命令执行失败。",
            }
    result = {
        "ok": True,
        "action": plan.get("action", ""),
        "executed": True,
        "commands": command_records,
        "exit_code": 0,
        "stdout": "".join(stdout_parts),
        "stderr": "".join(stderr_parts),
    }
    if str(plan.get("action", "")).strip().lower() == "commit":
        commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(plan.get("repo_path", "")),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        commit_subject = subprocess.run(
            ["git", "log", "-1", "--pretty=%s"],
            cwd=str(plan.get("repo_path", "")),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        command_records.extend([["git", "rev-parse", "HEAD"], ["git", "log", "-1", "--pretty=%s"]])
        result["commit_hash"] = commit_hash.stdout.strip() if commit_hash.returncode == 0 else ""
        result["commit_subject"] = commit_subject.stdout.strip() if commit_subject.returncode == 0 else ""
        result["stdout"] = str(result["stdout"]) + (commit_hash.stdout or "") + (commit_subject.stdout or "")
        result["stderr"] = str(result["stderr"]) + (commit_hash.stderr or "") + (commit_subject.stderr or "")
    return result


def build_final_output(
    markdown: str,
    decision: dict[str, Any],
    target_path: str,
    commit_message_suggestion: dict[str, str] | None = None,
    commit_action_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cleaned_markdown = markdown if markdown.endswith("\n") else f"{markdown}\n"
    commit_message_suggestion = commit_message_suggestion or {"message": "", "rationale": ""}
    normalized_decision = (
        decision
    if "commit_action" in decision
        else normalize_delivery_decision(decision, commit_message_suggestion=commit_message_suggestion["message"])
    )
    commit_action_result = commit_action_result or {
        "ok": True,
        "action": normalized_decision.get("commit_action", "none"),
        "executed": False,
        "commands": [],
    }
    return {
        "final_change_brief_markdown": cleaned_markdown,
        "delivery_decision": normalized_decision,
        "commit_message_suggestion": commit_message_suggestion["message"],
        "commit_message_suggestion_zh": commit_message_suggestion.get("message_zh", ""),
        "commit_message_rationale": commit_message_suggestion["rationale"],
        "commit_action_result": commit_action_result,
        "run_artifact_index": {
            "suggested_output_path": target_path,
            "artifacts": [
                ".lgwf/change_brief_markdown.json",
                ".lgwf/git_context_snapshot.json",
                ".lgwf/delivery_decision.json",
            ],
        },
    }


def main() -> None:
    lgwf_dir = Path(".lgwf")
    git_context = load_git_context(lgwf_dir)
    review_context = load_review_context(lgwf_dir)
    summary_context = load_summary_context(lgwf_dir)
    commit_suggestion = resolve_commit_message_suggestion(
        review_context=review_context,
        summary_context=summary_context,
        git_context=git_context,
    )
    confirmed_delivery = resolve_confirmed_delivery_action(review_context)
    decision = normalize_delivery_decision(
        load_delivery_decision(lgwf_dir),
        commit_message_suggestion=commit_suggestion["message"],
        default_commit_action=confirmed_delivery["commit_action"],
        default_commit_message=confirmed_delivery["commit_message"],
        default_allow_repo_root_write=bool(confirmed_delivery["allow_repo_root_write"]),
    )
    commit_plan = build_commit_plan(decision, git_context)
    result = build_final_output(
        markdown=load_markdown(lgwf_dir),
        decision=decision,
        target_path="artifacts/git-diff-brief.md",
        commit_message_suggestion=commit_suggestion,
    )
    delivery_decision_path = lgwf_dir / "delivery_decision.json"
    delivery_decision_path.write_text(
        json.dumps(result["delivery_decision"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    commit_plan_path = lgwf_dir / "commit_plan.json"
    commit_plan_path.write_text(json.dumps(commit_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "git_diff_brief.final_change_brief_markdown": result["final_change_brief_markdown"],
        "git_diff_brief.delivery_decision": result["delivery_decision"],
        "git_diff_brief.commit_message_suggestion": result["commit_message_suggestion"],
        "git_diff_brief.commit_message_suggestion_zh": result["commit_message_suggestion_zh"],
        "git_diff_brief.commit_message_rationale": result["commit_message_rationale"],
        "git_diff_brief.commit_plan": commit_plan,
        "git_diff_brief.run_artifact_index": result["run_artifact_index"],
        "git_diff_brief.finalize_output_result": {
            "ok": bool(commit_plan.get("ok")),
            "commit_plan_file": ".lgwf/commit_plan.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
