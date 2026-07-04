from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any


WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s，,。；;]+")
POSIX_PATH_RE = re.compile(r"/[^\s，,。；;]+")


def normalize_repo_hint(raw: str) -> str:
    cleaned = str(raw or "").strip().rstrip("\\/")
    if not cleaned:
        return ""
    return PurePosixPath(cleaned.replace("\\", "/")).as_posix()


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


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not raw.strip():
        return load_runtime_input()
    data = json.loads(raw)
    if not isinstance(data, dict):
        return load_runtime_input()
    state = data.get("state")
    if isinstance(state, dict):
        return state
    return data


def extract_repo_from_revision(path: Path = Path(".lgwf/request_scope_confirmation.json")) -> str:
    data = load_json(path, {})
    value = data.get("value", data)
    if not isinstance(value, dict):
        return ""
    if str(value.get("approval", value.get("decision", ""))).strip().lower() != "revise":
        return ""
    texts: list[str] = []
    changes = value.get("changes", [])
    if isinstance(changes, list):
        for item in changes:
            if isinstance(item, dict) and str(item.get("field", "")).strip() in {"repo_path", "repo_hint", "repository"}:
                return normalize_repo_hint(str(item.get("value", "")))
            texts.append(str(item))
    comment = value.get("comment")
    if comment:
        texts.append(str(comment))
    joined = "\n".join(texts)
    for pattern in (WINDOWS_PATH_RE, POSIX_PATH_RE):
        match = pattern.search(joined)
        if match:
            return normalize_repo_hint(match.group(0))
    return ""


def has_revision(path: Path = Path(".lgwf/request_scope_confirmation.json")) -> bool:
    data = load_json(path, {})
    value = data.get("value", data)
    if not isinstance(value, dict):
        return False
    return str(value.get("approval", value.get("decision", ""))).strip().lower() == "revise"


def nested_dict(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def build_capture(state: dict[str, Any]) -> dict[str, Any]:
    nested_input = state.get("input")
    source = nested_input if isinstance(nested_input, dict) else state
    git_diff_state = nested_dict(state, "git_diff_brief")
    validation = nested_dict(git_diff_state, "request_scope_validation")
    normalized = normalize_repo_hint(
        str(
            git_diff_state.get("normalized_repo_hint")
            or source.get("repo_path")
            or source.get("repo_hint")
            or source.get("repository")
            or extract_repo_from_revision()
        )
    )
    requested_extensions = validation.get("requested_extensions", source.get("requested_extensions", []))
    if not isinstance(requested_extensions, list):
        requested_extensions = [requested_extensions]
    requested_extensions = [str(item) for item in requested_extensions if str(item).strip()]
    if has_revision():
        requested_extensions = []
    path_exists = bool(validation.get("path_exists", bool(normalized)))
    needs_confirmation = not normalized or not path_exists or bool(requested_extensions)
    open_questions: list[str] = []
    if not normalized:
        open_questions.append("请提供需要生成变更摘要的仓库目录提示或确认目标仓库路径。")
    if not path_exists:
        open_questions.append("当前仓库路径校验未通过，请确认有效的 Git 仓库目录。")
    open_questions.extend(requested_extensions)
    return {
        "repository_input_context": {
            "repo_hint": normalized or None,
            "normalized_repo_hint": normalized or None,
            "path_exists": path_exists if normalized else None,
        },
        "summary_scope": {
            "baseline": "worktree git diff + latest commit",
            "requested_extensions": requested_extensions,
        },
        "scope_confirmation_input": {
            "needs_confirmation": needs_confirmation,
            "open_questions": open_questions,
            "recommended_decision": "revise" if needs_confirmation else "approve",
        },
        "needs_confirmation": needs_confirmation,
        "open_questions": open_questions,
    }


def main() -> None:
    capture = build_capture(read_stdin_payload())
    output_path = Path(".lgwf/request_scope_capture.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(capture, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "git_diff_brief.repository_input_context": capture["repository_input_context"],
        "git_diff_brief.summary_scope": capture["summary_scope"],
        "git_diff_brief.scope_confirmation_input": capture["scope_confirmation_input"],
        "git_diff_brief.request_scope_capture_result": {
            "ok": True,
            "output_file": ".lgwf/request_scope_capture.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
