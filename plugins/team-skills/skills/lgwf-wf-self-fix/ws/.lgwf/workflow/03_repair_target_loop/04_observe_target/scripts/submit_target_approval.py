from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state, read_json, run_lgwf


def normalize_decision(raw: dict, request_context: dict) -> tuple[str, str | None, str | None]:
    decision = raw.get("decision") or raw.get("approval")
    if decision not in {"approve", "reject"}:
        raise ValueError("target approval decision must be approve or reject")
    if decision == "approve":
        value = raw.get("value")
        if value is None:
            value = request_context.get("context", {})
        return "approve", json.dumps(value, ensure_ascii=False), raw.get("comment") or "user approved"
    comment = raw.get("comment")
    if not isinstance(comment, str) or not comment.strip():
        raise ValueError("reject requires a non-empty comment")
    return "reject", None, comment


def main() -> None:
    root = lgwf_dir()
    approval_context = read_json(root / "target_approval_context.json", {})
    if not isinstance(approval_context, dict):
        raise ValueError(".lgwf/target_approval_context.json must contain a JSON object")
    decision_raw = read_json(root / "target_approval_decision.json", {})
    if not isinstance(decision_raw, dict):
        raise ValueError(".lgwf/target_approval_decision.json must contain a JSON object")
    request = approval_context.get("request")
    if not isinstance(request, dict):
        request = {}
    decision, value_json, comment = normalize_decision(decision_raw, request)
    args = [
        "approval",
        "submit",
        "--work-dir",
        approval_context["work_dir"],
        "--request-id",
        approval_context["request_id"],
        "--decision",
        decision,
    ]
    if value_json is not None:
        args.extend(["--value-json", value_json])
    if comment is not None:
        args.extend(["--comment", comment])
    proc = run_lgwf(args, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"failed to submit target approval: {proc.stderr or proc.stdout}")
    append_history({"event": "target_approval_submitted", "request_id": approval_context["request_id"], "decision": decision})
    output_state({"target_approval_submitted": True, "target_approval_submit_stdout": proc.stdout, "next_action": "observe"})


if __name__ == "__main__":
    main()
