from __future__ import annotations

import json
import sys
from pathlib import Path

from lgwf_client.main_agent.approvals import submit_main_agent_approval

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state, read_json
from target_repair_loop import load_current_artifact


def has_existing_response(work_dir: Path, request_id: str) -> bool:
    return (work_dir / ".lgwf" / "human" / f"{request_id}.response.json").is_file()


def load_approval_context(root: Path) -> dict:
    approval = load_current_artifact(root, "approval", {})
    if not isinstance(approval, dict):
        raise ValueError(".lgwf/target_repair/current/approval.json must contain a JSON object")
    if not approval.get("work_dir") or not approval.get("request_id"):
        raise ValueError("approval.json must contain work_dir and request_id")
    return approval


def normalize_decision(raw: dict, request_context: dict) -> tuple[str, object | None, str | None]:
    decision = raw.get("decision") or raw.get("approval")
    if decision not in {"approve", "reject"}:
        raise ValueError("target approval decision must be approve or reject")
    if decision == "approve":
        value = raw.get("value", {})
        return "approve", value, raw.get("comment") or "user approved"
    comment = raw.get("comment")
    if not isinstance(comment, str) or not comment.strip():
        raise ValueError("reject requires a non-empty comment")
    return "reject", None, comment


def main() -> None:
    root = lgwf_dir()
    approval_context = load_approval_context(root)
    decision_raw = read_json(root / "target_approval_decision.json", {})
    if not isinstance(decision_raw, dict):
        raise ValueError(".lgwf/target_approval_decision.json must contain a JSON object")
    request = approval_context.get("request")
    if not isinstance(request, dict):
        request = {}
    decision, value, comment = normalize_decision(decision_raw, request)
    work_dir = Path(approval_context["work_dir"])
    request_id = str(approval_context["request_id"])
    if has_existing_response(work_dir, request_id):
        append_history({"event": "target_approval_already_submitted", "request_id": request_id})
        output_state({"target_approval_submitted": True, "target_approval_already_submitted": True, "next_action": "observe"})
        return
    result = submit_main_agent_approval(
        work_dir,
        request_id,
        decision=decision,
        value=value,
        comment=comment,
    )
    append_history({"event": "target_approval_submitted", "request_id": request_id, "decision": decision})
    output_state({"target_approval_submitted": True, "target_approval_submit_result": result, "next_action": "observe"})


if __name__ == "__main__":
    main()
