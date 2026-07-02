from __future__ import annotations

import json
from pathlib import Path


def load_review_context(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "delivery_review_input": {
                "final_change_brief_markdown": "# 变更摘要\n\n待补齐。\n",
                "commit_message_suggestion": "chore(git-diff-brief): summarize scoped git diff changes",
                "commit_message_rationale": "缺少 delivery_review_context.json，使用保守提交信息建议。",
                "commit_action_options": ["none", "stage", "commit"],
                "default_commit_action": "none",
                "open_delivery_questions": ["缺少 delivery_review_context.json，需补齐结果展示输出。"],
            }
        }
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    review = load_review_context(Path(".lgwf/delivery_review_context.json"))
    payload = {
        "git_diff_brief.delivery_review_input": review.get("delivery_review_input", review),
        "git_diff_brief.prepare_delivery_review_result": {
            "ok": True,
            "source_file": ".lgwf/delivery_review_context.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
