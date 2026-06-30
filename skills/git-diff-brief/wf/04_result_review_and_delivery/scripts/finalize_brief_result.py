from __future__ import annotations

import json
from typing import Any


def build_final_output(markdown: str, decision: dict[str, Any], target_path: str) -> dict[str, Any]:
    cleaned_markdown = markdown if markdown.endswith("\n") else f"{markdown}\n"
    normalized_decision = {
        "decision": str(decision.get("decision", "")).strip().lower() or "approve",
        "comment": str(decision.get("comment", "")).strip(),
        "changes": decision.get("changes", []) if isinstance(decision.get("changes", []), list) else [],
    }
    return {
        "final_change_brief_markdown": cleaned_markdown,
        "delivery_decision": normalized_decision,
        "run_artifact_index": {
            "suggested_output_path": target_path,
            "artifacts": [
                ".lgwf/change_brief_markdown.json",
                ".lgwf/delivery_decision.json",
            ],
        },
    }


def main() -> None:
    result = build_final_output(
        markdown="# 变更摘要\n\n待补齐最终 Markdown 内容。\n",
        decision={"decision": "approve", "comment": "placeholder"},
        target_path="artifacts/git-diff-brief.md",
    )
    payload = {
        "git_diff_brief.final_change_brief_markdown": result["final_change_brief_markdown"],
        "git_diff_brief.delivery_decision": result["delivery_decision"],
        "git_diff_brief.run_artifact_index": result["run_artifact_index"],
        "git_diff_brief.finalize_output_result": {
            "ok": True,
            "placeholder": True,
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
