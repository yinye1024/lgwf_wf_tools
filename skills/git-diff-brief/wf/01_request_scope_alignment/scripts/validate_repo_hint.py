from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any


WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s，,。；;]+")
POSIX_PATH_RE = re.compile(r"/[^\s，,。；;]+")
REVISION_TARGET_RE = re.compile(r"(?:改为|to)\s+([^\s，,。；;]+)")


def normalize_repo_hint(raw: str) -> str:
    cleaned = str(raw or "").strip()
    cleaned = cleaned.rstrip("\\/")
    if not cleaned:
        raise ValueError("repo_hint 不能为空")
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if any(part == ".lgwf" for part in candidate.parts):
        raise ValueError("repo_hint 不得指向 .lgwf 运行状态目录")
    return candidate.as_posix()


def repo_hint_from_revision(revision: dict[str, Any]) -> str:
    texts: list[str] = []
    changes = revision.get("changes", [])
    if isinstance(changes, list):
        texts.extend(str(item) for item in changes)
    elif changes:
        texts.append(str(changes))
    comment = revision.get("comment")
    if comment:
        texts.append(str(comment))
    joined = "\n".join(texts)
    for pattern in (REVISION_TARGET_RE, WINDOWS_PATH_RE, POSIX_PATH_RE):
        match = pattern.search(joined)
        if match:
            return normalize_repo_hint(match.group(1) if match.lastindex else match.group(0))
    return ""


def load_revision_repo_hint(path: str = ".lgwf/request_scope_confirmation.json") -> str:
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return ""
    if not isinstance(payload, dict):
        return ""
    value = payload.get("value", payload)
    if not isinstance(value, dict):
        return ""
    approval = str(value.get("approval", value.get("decision", ""))).strip().lower()
    if approval != "revise":
        return ""
    return repo_hint_from_revision(value)


def load_runtime_input(root: Path = Path(".lgwf/checkpoints")) -> dict[str, Any]:
    if not root.exists():
        return {}
    checkpoints = sorted(root.glob("*/checkpoint.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in checkpoints:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            continue
        state = data.get("state_before_current_node", {})
        if isinstance(state, dict):
            return state
    return {}


def build_scope_validation(input_state: dict[str, Any]) -> dict[str, Any]:
    nested_input = input_state.get("input")
    source = nested_input if isinstance(nested_input, dict) else input_state
    repo_hint = (
        source.get("repo_path")
        or source.get("repo_hint")
        or source.get("repository")
        or input_state.get("repo_path")
        or input_state.get("repo_hint")
        or input_state.get("repository")
        or load_revision_repo_hint()
    )
    normalized = normalize_repo_hint(repo_hint)
    requested_extensions = source.get("requested_extensions", input_state.get("requested_extensions", []))
    if not isinstance(requested_extensions, list):
        requested_extensions = [requested_extensions]
    needs_confirmation = bool(requested_extensions)
    return {
        "normalized_repo_hint": normalized,
        "request_scope_validation": {
            "path_exists": True,
            "baseline_scope": "worktree git diff + latest commit",
            "requested_extensions": [str(item) for item in requested_extensions if str(item).strip()],
            "needs_confirmation": needs_confirmation,
        },
        "scope_confirmation_input": {
            "needs_confirmation": needs_confirmation,
            "open_questions": [str(item) for item in requested_extensions if str(item).strip()],
            "recommended_decision": "revise" if needs_confirmation else "approve",
        },
    }


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not raw.strip():
        return load_runtime_input()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("stdin payload 必须是 JSON object")
    state_input = payload.get("input")
    if isinstance(state_input, dict):
        return state_input
    state = payload.get("state")
    if isinstance(state, dict) and isinstance(state.get("input"), dict):
        return state["input"]
    return payload or load_runtime_input()


def main() -> None:
    try:
        payload = build_scope_validation(read_stdin_payload())
    except ValueError as exc:
        payload = {
            "git_diff_brief.request_scope_validation_result": {
                "ok": False,
                "error": str(exc),
            }
        }
    else:
        payload = {
            "git_diff_brief.normalized_repo_hint": payload["normalized_repo_hint"],
            "git_diff_brief.request_scope_validation": payload["request_scope_validation"],
            "git_diff_brief.scope_confirmation_input": payload["scope_confirmation_input"],
            "git_diff_brief.request_scope_validation_result": {
                "ok": True,
                "normalized_repo_hint": payload["normalized_repo_hint"],
            },
        }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
