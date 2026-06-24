from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir
from target_repair_loop import load_current_artifact, record_decision


def choose_decision(plan: dict, verification: dict, apply_result: dict | None = None) -> dict:
    apply_result = apply_result or {}
    if plan.get("status") == "blocked":
        return {
            "category": "block",
            "stop_reason": "plan_blocked",
            "reason": plan.get("blocked_reason") or "repair plan is blocked",
            "evidence": plan.get("evidence") or [],
        }
    if apply_result.get("status") == "blocked":
        return {
            "category": "retry",
            "stop_reason": "apply_blocked",
            "reason": apply_result.get("reason") or "repair application was blocked",
            "evidence": apply_result.get("evidence") or [],
        }
    if verification.get("passed") is True:
        if verification.get("semantic_review_needed") is True:
            return {
                "category": "retry",
                "stop_reason": "semantic_review_needed",
                "reason": "repair candidate passed deterministic checks but still has semantic evidence gaps",
                "evidence": verification.get("semantic_risks") or [],
            }
        return {
            "category": "finish",
            "stop_reason": "repair_candidate_ready",
            "reason": "repair candidate passed validation and is ready to promote",
            "evidence": verification.get("checks") or [],
        }
    return {
        "category": "retry",
        "stop_reason": "verification_failed",
        "reason": "repair candidate did not pass verification; start another agent-loop iteration",
        "evidence": verification.get("issues") or [],
    }


def main() -> None:
    root = lgwf_dir()
    plan = load_current_artifact(root, "plan", {})
    verification = load_current_artifact(root, "verification", {})
    apply_result = load_current_artifact(root, "apply", {})
    if not isinstance(plan, dict):
        plan = {}
    if not isinstance(verification, dict):
        verification = {}
    if not isinstance(apply_result, dict):
        apply_result = {}
    decision = choose_decision(plan, verification, apply_result)
    record_decision(root, decision)
    append_history({"event": "repair_agent_loop_decided", "decision": decision})
    print(json.dumps({"lgwf_wf_fix.target_repair_loop_decision": decision}, ensure_ascii=False))


if __name__ == "__main__":
    main()
