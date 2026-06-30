from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state
from target_repair_loop import load_current_artifact, record_decision


def choose_decision(target: dict, observation: dict | None = None) -> dict:
    observation = observation or {}
    status = observation.get("status") or target.get("last_status")
    if status == "waiting_approval":
        if target.get("ask_main_agent_for_target_approvals") is not True:
            return {
                "route": "finish",
                "category": "block",
                "stop_reason": "target_waiting_approval_main_agent_confirmation_disabled",
                "reason": "target workflow is waiting for approval and ask_main_agent_for_target_approvals is false",
            }
        return {"route": "approval", "category": "wait_human", "reason": "target workflow is waiting for approval"}
    if status == "succeeded":
        health = observation.get("run_health") if isinstance(observation.get("run_health"), dict) else {}
        degraded = bool(
            health.get("data_fallback")
            or health.get("codex_stream_disconnects")
            or health.get("codex_http_fallbacks")
        )
        return {
            "route": "finish",
            "category": "finish",
            "stop_reason": "target_succeeded_with_warnings" if degraded else "target_succeeded",
            "reason": "target workflow succeeded",
            "evidence": health,
        }
    if status in {"failed", "needs_repair"}:
        attempt = int(target.get("current_attempt", 0))
        max_attempts = int(target.get("max_attempts", 5))
        if attempt >= max_attempts:
            return {
                "route": "finish",
                "category": "block",
                "stop_reason": "max_attempts_reached",
                "reason": "target repair reached max attempts",
                "evidence": [f"attempt={attempt}", f"max_attempts={max_attempts}"],
            }
        return {
            "route": "fix",
            "category": "continue",
            "reason": "target workflow needs repair",
            "failure_class": observation.get("failure_class") or "unknown",
            "evidence": observation.get("issues") or observation.get("status_detail") or [],
        }
    if status == "running":
        return {"route": "observe", "category": "wait", "reason": "target workflow is still running"}
    return {
        "route": "fix",
        "category": "continue",
        "reason": "target status is unknown; try repair diagnosis",
        "failure_class": "unknown",
    }


def choose_route(target: dict) -> str:
    return str(choose_decision(target)["route"])


def main() -> None:
    target = load_self_fix_target()
    root = lgwf_dir()
    observation = load_current_artifact(root, "observation", {})
    if not isinstance(observation, dict):
        observation = {}
    decision = choose_decision(target, observation)
    route = str(decision["route"])
    record_decision(root, decision)
    append_history({"event": "route_after_observe", "route": route, "decision": decision, "status": target.get("last_status")})
    output_state({"next_action": route}, next_key=route, route_node="route_after_observe")


if __name__ == "__main__":
    main()
