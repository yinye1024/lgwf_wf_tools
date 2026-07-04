from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_capture(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "repository_input_context": {},
            "summary_scope": {},
            "scope_confirmation_input": {
                "needs_confirmation": True,
                "open_questions": ["缺少 request_scope_capture.json，需补齐第一阶段输出。"],
                "recommended_decision": "revise",
            },
        }
    return json.loads(path.read_text(encoding="utf-8"))


def read_state() -> dict[str, Any]:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        return {}
    state = data.get("state")
    return state if isinstance(state, dict) else data


def nested_dict(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def merge_validated_scope(capture: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    context = capture.get("repository_input_context")
    context = context if isinstance(context, dict) else {}
    if context.get("normalized_repo_hint") or context.get("repo_hint"):
        return capture

    git_diff_state = nested_dict(state, "git_diff_brief")
    normalized = str(git_diff_state.get("normalized_repo_hint", "")).strip()
    validation = nested_dict(git_diff_state, "request_scope_validation")
    if not normalized or not validation.get("path_exists", True):
        return capture

    requested_extensions = validation.get("requested_extensions", [])
    if not isinstance(requested_extensions, list):
        requested_extensions = [requested_extensions]
    requested_extensions = [str(item) for item in requested_extensions if str(item).strip()]
    capture = dict(capture)
    capture["repository_input_context"] = {
        "repo_hint": normalized,
        "normalized_repo_hint": normalized,
        "path_exists": True,
    }
    capture["summary_scope"] = capture.get("summary_scope") or {
        "baseline": "worktree git diff + latest commit",
        "requested_extensions": requested_extensions,
    }
    capture["scope_confirmation_input"] = {
        "needs_confirmation": bool(requested_extensions),
        "open_questions": requested_extensions,
        "recommended_decision": "revise" if requested_extensions else "approve",
    }
    return capture


def main() -> None:
    capture = merge_validated_scope(load_capture(Path(".lgwf/request_scope_capture.json")), read_state())
    payload = {
        "git_diff_brief.repository_input_context": capture.get("repository_input_context", {}),
        "git_diff_brief.summary_scope": capture.get("summary_scope", {}),
        "git_diff_brief.scope_confirmation_input": capture.get("scope_confirmation_input", {}),
        "git_diff_brief.prepare_scope_confirmation_result": {
            "ok": True,
            "source_file": ".lgwf/request_scope_capture.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
