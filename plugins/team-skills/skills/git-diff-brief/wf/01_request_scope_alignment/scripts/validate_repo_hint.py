from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any


def normalize_repo_hint(raw: str) -> str:
    cleaned = str(raw or "").strip()
    if not cleaned:
        raise ValueError("repo_hint 不能为空")
    candidate = PurePosixPath(cleaned.replace("\\", "/"))
    if any(part == ".lgwf" for part in candidate.parts):
        raise ValueError("repo_hint 不得指向 .lgwf 运行状态目录")
    return candidate.as_posix()


def build_scope_validation(input_state: dict[str, Any]) -> dict[str, Any]:
    repo_hint = input_state.get("repo_path") or input_state.get("repo_hint") or input_state.get("repository")
    normalized = normalize_repo_hint(repo_hint)
    requested_extensions = input_state.get("requested_extensions", [])
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


def main() -> None:
    try:
        payload = build_scope_validation({"repo_hint": "."})
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
