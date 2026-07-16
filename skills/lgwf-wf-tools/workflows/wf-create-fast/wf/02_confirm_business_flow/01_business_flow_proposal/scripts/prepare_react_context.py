"""准备业务流 proposal ReAct 每轮的紧凑上下文。"""

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


def nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def first_text(candidates: list[dict[str, Any]], keys: tuple[str, ...]) -> str:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


def identity_candidates(*items: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in items:
        if not item:
            continue
        candidates.append(item)
        for key in ("confirmed", "target_identity", "identity", "request"):
            nested = nested_dict(item, key)
            if nested:
                candidates.append(nested)
    return candidates


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
    requirements = read_json(lgwf_dir / "create_requirements.json")
    requirements_proposal = read_json(lgwf_dir / "create_requirements_proposal.json")
    gate = read_json(lgwf_dir / "business_flow_proposal_quality_gate.json")
    decision = read_json(lgwf_dir / "business_flow_proposal_decision.json")
    candidates = identity_candidates(requirements, requirements_proposal)
    has_previous_gate = bool(gate)
    passed = gate.get("passed") is True
    failures = failed_checks(gate)
    return {
        "requirements_file": ".lgwf/create_requirements.json",
        "requirements_proposal_file": ".lgwf/create_requirements_proposal.json",
        "proposal_file": ".lgwf/business_flow_proposal.json",
        "quality_gate_file": ".lgwf/business_flow_proposal_quality_gate.json",
        "current_target": {
            "workflow_id": first_text(candidates, ("workflow_id", "workflow_name", "name")),
            "workflow_name": first_text(candidates, ("workflow_name", "name")),
            "target_package_root": first_text(candidates, ("target_package_root", "package_root")),
        },
        "confirmed_requirements": nested_dict(requirements, "confirmed") or requirements,
        "requirements_proposal": requirements_proposal,
        "previous_business_flow": {},
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
            else "第一轮生成 .lgwf/business_flow_proposal.json。"
            if not has_previous_gate
            else "根据 failed_checks 修复 .lgwf/business_flow_proposal.json；不要扩大到脚手架落盘或具体实现。"
        ),
    }


def main() -> None:
    context = build_context(Path.cwd())
    write_json(Path.cwd() / ".lgwf" / "business_flow_proposal_react_context.json", context)
    print(json.dumps({"lgwf_wf_create_fast.business_flow_proposal_react_context": context}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
