from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir
from target_repair_loop import load_current_artifact, write_current_artifact


def _review_required(verification: dict[str, Any]) -> bool:
    return verification.get("passed") is True and verification.get("semantic_review_needed") is True


def finalize_verification(verification: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    result = dict(verification)
    if not _review_required(verification):
        result["semantic_review"] = {"status": "not_required"}
        return result

    if not review:
        result["semantic_review"] = {
            "status": "missing",
            "reason": "semantic_review_needed=true but review.json was not produced",
        }
        result["semantic_review_needed"] = True
        result["semantic_risks"] = [
            {
                "name": "semantic_review_missing",
                "risk": "确定性校验要求语义审查，但 review 节点没有产出 review.json。",
                "next_agent_action": "重新运行语义审查，或检查 review_repair_candidate prompt 是否写入 .lgwf/target_repair/current/review.json。",
            }
        ]
        result["retry_hints"] = [
            *list(result.get("retry_hints") or []),
            "semantic_review_needed=true 但缺少 review.json，需要重新运行语义审查或修复 review prompt 输出。",
        ]
        return result

    result["semantic_review"] = review
    if review.get("status") == "pass":
        result["semantic_review_needed"] = False
        result["semantic_risks"] = []
    else:
        issues = review.get("semantic_issues") or review.get("evidence") or []
        result["semantic_review_needed"] = True
        result["semantic_risks"] = issues
        result["retry_hints"] = [
            *list(result.get("retry_hints") or []),
            review.get("next_agent_action") or "根据语义审查结果补齐根因、计划步骤映射和变更证据。",
        ]
    return result


def main() -> None:
    root = lgwf_dir()
    verification = load_current_artifact(root, "verification", {})
    review = load_current_artifact(root, "review", {})
    if not isinstance(verification, dict):
        verification = {}
    if not isinstance(review, dict):
        review = {}
    result = finalize_verification(verification, review)
    write_current_artifact(root, "verification", result)
    append_history(
        {
            "event": "repair_candidate_review_finalized",
            "passed": result.get("passed"),
            "semantic_review_needed": result.get("semantic_review_needed"),
            "review_status": (result.get("semantic_review") or {}).get("status"),
        }
    )
    print(json.dumps({"lgwf_wf_fix.target_repair_current_verification": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
