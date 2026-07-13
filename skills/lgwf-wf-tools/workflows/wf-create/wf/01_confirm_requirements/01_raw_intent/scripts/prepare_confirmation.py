"""根据启动输入准备 raw intent 候选对象和确认上下文。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


PROPOSAL_FILE = "raw_intent_request_proposal.json"


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if raw:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("stdin payload 必须是 JSON object")
        return payload
    fallback = Path.cwd() / ".lgwf" / "input_state.json"
    if fallback.is_file():
        payload = json.loads(fallback.read_text(encoding="utf-8-sig"))
        if isinstance(payload, dict):
            return payload
    return {}


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return []


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def build_raw_intent_request(payload: dict[str, Any]) -> dict[str, Any]:
    request = payload.get("request")
    if not isinstance(request, dict):
        request = {}
    context_dirs = _dedupe(
        _as_string_list(request.get("target_dir"))
        + _as_string_list(request.get("target_dirs"))
        + _as_string_list(payload.get("creation_context_dirs"))
    )
    context_files = _dedupe(
        _as_string_list(request.get("target_file"))
        + _as_string_list(request.get("target_files"))
        + _as_string_list(payload.get("creation_context_files"))
    )
    raw_intent = payload.get("raw_intent")
    goal = payload.get("goal")
    constraints = payload.get("constraints")
    target_package_hint = payload.get("target_package_hint")
    result: dict[str, Any] = {
        "raw_intent": raw_intent.strip() if isinstance(raw_intent, str) else "",
        "goal": goal.strip() if isinstance(goal, str) else "",
        "constraints": _as_string_list(constraints),
        "target_package_hint": target_package_hint.strip() if isinstance(target_package_hint, str) else "",
        "creation_context_dirs": context_dirs,
        "creation_context_files": context_files,
        "open_questions": _as_string_list(payload.get("open_questions")),
        "request": request,
    }
    for key in ("source_business_contract", "conversion_mapping", "prompt_workflow_context"):
        if key in payload:
            result[key] = payload[key]
    return result


def build_confirmation_context(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": "确认原始意图",
        "review_node": "confirm_raw_intent",
        "approval_target": "raw_intent_request_proposal",
        "approve_writes": ".lgwf/raw_intent_request.json",
        "persist_path": ".lgwf/raw_intent_approval.json",
        "allowed_decisions": ["approve", "revise", "reject"],
        "proposal": proposal,
        "review_context_json": {
            "review_node": "confirm_raw_intent",
            "approval_target": "raw_intent_request_proposal",
            "approve_writes": ".lgwf/raw_intent_request.json",
            "persist_path": ".lgwf/raw_intent_approval.json",
            "proposal": proposal,
            "allowed_decisions": ["approve", "revise", "reject"],
        },
        "revise_instruction": "revise 必须提交完整 raw_intent_request JSON；approve 不需要提交业务 value。",
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    payload = read_stdin_payload()
    proposal = build_raw_intent_request(payload)
    context = build_confirmation_context(proposal)
    lgwf_dir = Path.cwd() / ".lgwf"
    write_json(lgwf_dir / PROPOSAL_FILE, proposal)
    print(
        json.dumps(
            {
                "lgwf_wf_create.raw_intent_request_proposal": proposal,
                "lgwf_wf_create.raw_intent_confirmation_context": context,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
