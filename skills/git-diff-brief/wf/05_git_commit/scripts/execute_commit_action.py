from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve()
RESULT_STAGE_SCRIPTS = CURRENT_DIR.parents[2] / "04_result_review_and_delivery" / "scripts"
if str(RESULT_STAGE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(RESULT_STAGE_SCRIPTS))

from finalize_brief_result import (  # noqa: E402
    build_commit_plan,
    execute_commit_action,
    load_delivery_decision,
    load_git_context,
    load_json,
    load_review_context,
    load_summary_context,
    normalize_delivery_decision,
    resolve_commit_message_suggestion,
)


def load_or_build_commit_plan(lgwf_dir: Path) -> dict[str, Any]:
    plan = load_json(lgwf_dir / "commit_plan.json", {})
    if plan and (plan.get("ok") is True or str(plan.get("action", "")) == "none"):
        return plan
    git_context = load_git_context(lgwf_dir)
    suggestion = resolve_commit_message_suggestion(
        review_context=load_review_context(lgwf_dir),
        summary_context=load_summary_context(lgwf_dir),
        git_context=git_context,
    )
    decision = normalize_delivery_decision(
        load_delivery_decision(lgwf_dir),
        commit_message_suggestion=suggestion["message"],
    )
    return build_commit_plan(decision, git_context)


def main() -> None:
    lgwf_dir = Path(".lgwf")
    plan = load_or_build_commit_plan(lgwf_dir)
    result = execute_commit_action(plan)
    output_path = lgwf_dir / "commit_action_result.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {
        "git_diff_brief.commit_action_result": result,
        "git_diff_brief.execute_commit_action_result": {
            "ok": bool(result.get("ok")),
            "output_file": ".lgwf/commit_action_result.json",
        },
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
