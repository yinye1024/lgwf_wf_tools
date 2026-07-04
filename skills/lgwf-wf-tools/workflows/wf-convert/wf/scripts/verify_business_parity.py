from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text_blob(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).lower()


def item_id(item: Any, fallback_prefix: str, index: int) -> str:
    if isinstance(item, dict):
        for key in ("rule_id", "requirement_id", "stage_id", "name", "id"):
            raw = str(item.get(key, "")).strip()
            if raw:
                return raw
    return f"{fallback_prefix}-{index + 1}"


def is_covered(item: Any, mapping_blob: str) -> bool:
    if not mapping_blob:
        return False
    candidates: list[str] = []
    if isinstance(item, dict):
        for key in ("rule_id", "requirement_id", "stage_id", "name", "description", "objective"):
            raw = str(item.get(key, "")).strip().lower()
            if raw:
                candidates.append(raw)
    else:
        candidates.append(str(item).strip().lower())
    return any(candidate in mapping_blob for candidate in candidates if candidate)


def missing_items(items: list[Any], mapping_blob: str, fallback_prefix: str) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not is_covered(item, mapping_blob):
            missing.append(
                {
                    "rule_id": item_id(item, fallback_prefix, index),
                    "description": item.get("description", item.get("objective", "")) if isinstance(item, dict) else str(item),
                }
            )
    return missing


def build_parity_report(
    *,
    prompt_convert_payload: dict[str, Any],
    created_workflow: dict[str, Any],
) -> dict[str, Any]:
    contract = prompt_convert_payload.get("source_business_contract")
    if not isinstance(contract, dict):
        contract = {}
    context = prompt_convert_payload.get("prompt_workflow_context")
    if not isinstance(context, dict):
        context = {}
    mapping = as_list(prompt_convert_payload.get("conversion_mapping"))
    mapping_blob = text_blob(mapping)

    missing_business_rules = []
    missing_business_rules.extend(missing_items(as_list(contract.get("decision_rules")), mapping_blob, "decision-rule"))
    missing_business_rules.extend(missing_items(as_list(contract.get("invariants")), mapping_blob, "invariant"))
    missing_approval_points = missing_items(as_list(contract.get("approval_points")), mapping_blob, "approval-point")
    missing_error_paths = missing_items(as_list(contract.get("error_paths")), mapping_blob, "error-path")

    covered_business_rules = []
    for index, item in enumerate(as_list(contract.get("decision_rules")) + as_list(contract.get("invariants"))):
        if is_covered(item, mapping_blob):
            covered_business_rules.append({"rule_id": item_id(item, "covered-rule", index)})

    blocking_missing = missing_business_rules or missing_approval_points or missing_error_paths
    parity_verdict = "revise" if blocking_missing else "pass"
    return {
        "parity_verdict": parity_verdict,
        "created_workflow": created_workflow,
        "covered_business_rules": covered_business_rules,
        "missing_business_rules": missing_business_rules,
        "missing_approval_points": missing_approval_points,
        "missing_error_paths": missing_error_paths,
        "extra_behavior_risks": [],
        "discarded_prompt_techniques_checked": as_list(context.get("discarded_prompt_techniques")),
        "report_path": ".lgwf/business_parity_report.json",
    }


def read_stdin_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    data = json.loads(raw) if raw else {}
    return data if isinstance(data, dict) else {}


def load_prompt_convert_payload(root: Path) -> dict[str, Any]:
    path = root / ".lgwf" / "wf_create_payload.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return {}
    payload = data.get("prompt_convert_payload")
    return payload if isinstance(payload, dict) else {}


def main() -> None:
    root = Path.cwd()
    summary = read_stdin_payload()
    created_workflow = summary.get("created_workflow") if isinstance(summary.get("created_workflow"), dict) else {}
    report = build_parity_report(
        prompt_convert_payload=load_prompt_convert_payload(root),
        created_workflow=created_workflow,
    )
    report_path = root / ".lgwf" / "business_parity_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"lgwf_wf_convert.business_parity_report": report}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
