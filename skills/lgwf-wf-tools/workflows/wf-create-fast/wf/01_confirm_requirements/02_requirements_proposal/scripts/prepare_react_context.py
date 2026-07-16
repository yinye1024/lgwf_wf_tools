"""准备需求 proposal ReAct 每轮的紧凑上下文。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def failed_checks(gate: dict[str, Any]) -> list[dict[str, Any]]:
    checks = gate.get("checks")
    if not isinstance(checks, list):
        return []
    return [
        {
            "name": str(item.get("name", "")),
            "message": str(item.get("message", "")),
        }
        for item in checks
        if isinstance(item, dict) and item.get("passed") is not True
    ]


def build_context(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    raw_intent = read_json(lgwf_dir / "raw_intent_request.json")
    gate = read_json(lgwf_dir / "create_requirements_proposal_quality_gate.json")
    decision = read_json(lgwf_dir / "create_requirements_proposal_decision.json")
    has_previous_gate = bool(gate)
    passed = gate.get("passed") is True
    failures = failed_checks(gate)
    return {
        "raw_intent_file": ".lgwf/raw_intent_request.json",
        "proposal_file": ".lgwf/create_requirements_proposal.json",
        "quality_gate_file": ".lgwf/create_requirements_proposal_quality_gate.json",
        "current_target": {
            "workflow_id": raw_intent.get("workflow_id") or raw_intent.get("workflow_name") or raw_intent.get("name") or "",
            "workflow_name": raw_intent.get("workflow_name") or raw_intent.get("name") or "",
            "target_package_root": raw_intent.get("target_package_root") or raw_intent.get("package_root") or "",
            "target_package_hint": raw_intent.get("target_package_hint") or "",
        },
        "previous_quality_gate": {
            "exists": has_previous_gate,
            "passed": passed,
            "failed_checks": failures,
            "expected_identity": gate.get("expected_identity", {}),
            "actual_identity": gate.get("actual_identity", {}),
            "reference_hints": gate.get("reference_hints", {}),
            "parse_error": gate.get("parse_error", ""),
        },
        "previous_decision": {
            "next": decision.get("next", ""),
            "reason": decision.get("reason", ""),
            "passed": decision.get("passed"),
        },
        "repair_instruction": (
            "上一轮质量闸已通过，本轮保持 proposal 与当前目标一致。"
            if passed
            else "第一轮生成 .lgwf/create_requirements_proposal.json。"
            if not has_previous_gate
            else "根据 failed_checks 修复 .lgwf/create_requirements_proposal.json；不要扩大到业务流、脚手架落盘或具体实现。"
        ),
    }


def main() -> None:
    context = build_context(Path.cwd())
    write_json(Path.cwd() / ".lgwf" / "create_requirements_proposal_react_context.json", context)
    print(json.dumps({"lgwf_wf_create_fast.requirements_proposal_react_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
