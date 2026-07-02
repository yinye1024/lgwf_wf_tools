from __future__ import annotations

import json


def build_validation_suggestions() -> dict[str, object]:
    return {
        "validation_suggestions": [
            "git status --short",
            "git diff --stat",
            "git log -1 --stat",
        ],
        "summary_supporting_context": {
            "source_of_truth": [
                "git_diff_snapshot",
                "latest_commit_context",
                "changed_files_index",
            ],
            "context_kind": "real_git_context",
        },
    }


def main() -> None:
    suggestions = build_validation_suggestions()
    payload = {
        "git_diff_brief.validation_suggestions": suggestions["validation_suggestions"],
        "git_diff_brief.summary_supporting_context": suggestions["summary_supporting_context"],
        "git_diff_brief.validation_suggestions_result": {
            "ok": True,
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
