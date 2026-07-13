"""合并 structural gate 与 semantic observation。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_FORBIDDEN_CHANGES = [
    "不得写入 .lgwf/step_designs.json",
    "不得重新设计已确认 business_flow",
    "不得新增 scaffold_plan 之外的根目录结构",
]


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
    return [item for item in checks if isinstance(item, dict) and item.get("passed") is not True]


def structural_issues(gate: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    for item in failed_checks(gate):
        name = str(item.get("name", "structural_check_failed"))
        message = str(item.get("message", "结构校验失败"))
        issues.append(
            {
                "issue_id": name,
                "severity": "blocker",
                "evidence": message,
                "target_path": name,
                "required_change": message,
                "source": "structural_gate",
            }
        )
    return issues


def semantic_issues(semantic: dict[str, Any]) -> list[dict[str, Any]]:
    value = semantic.get("blocking_issues")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def list_value(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    return value if isinstance(value, list) else []


def merge_reason_feedback(
    structural_blocking_issues: list[dict[str, Any]],
    semantic: dict[str, Any],
) -> dict[str, Any]:
    semantic_feedback = semantic.get("reason_feedback")
    feedback = semantic_feedback if isinstance(semantic_feedback, dict) else {}
    must_change = list_value(feedback, "must_change")
    for issue in structural_blocking_issues:
        must_change.append(
            {
                "issue_id": issue["issue_id"],
                "target": issue.get("target_path", ""),
                "instruction": issue.get("required_change", issue.get("evidence", "")),
            }
        )
    priority_issue_ids = [str(issue.get("issue_id", "")) for issue in structural_blocking_issues if issue.get("issue_id")]
    priority_issue_ids.extend(str(value) for value in list_value(feedback, "priority_issue_ids") if value)
    forbidden_changes = list(dict.fromkeys([*DEFAULT_FORBIDDEN_CHANGES, *[str(value) for value in list_value(feedback, "forbidden_changes")]]))
    return {
        "repair_mode": str(feedback.get("repair_mode", "targeted_repair") or "targeted_repair"),
        "priority_issue_ids": priority_issue_ids,
        "must_preserve": list_value(feedback, "must_preserve"),
        "must_change": must_change,
        "forbidden_changes": forbidden_changes,
        "act_instruction_patch": list_value(feedback, "act_instruction_patch"),
    }


def build_observation(root: Path) -> dict[str, Any]:
    lgwf_dir = root / ".lgwf"
    structural = read_json(lgwf_dir / "step_design_structural_gate.json")
    semantic = read_json(lgwf_dir / "step_design_semantic_observation.json")
    structural_passed = structural.get("passed") is True
    semantic_passed = semantic.get("semantic_passed") is True
    structural_blocking_issues = structural_issues(structural)
    blocking_issues = [*structural_blocking_issues, *semantic_issues(semantic)]
    issue_signatures = [
        str(issue.get("issue_id", ""))
        for issue in blocking_issues
        if str(issue.get("issue_id", "")).strip()
    ]
    passed = structural_passed and semantic_passed and not blocking_issues
    verdict = "pass" if passed else "revise"
    result = {
        "passed": passed,
        "verdict": verdict,
        "structural_passed": structural_passed,
        "semantic_passed": semantic_passed,
        "blocking_issues": blocking_issues,
        "failed_checks": failed_checks(structural),
        "issue_signatures": issue_signatures,
        "valid_parts_to_preserve": list_value(semantic, "valid_parts_to_preserve"),
        "reason_feedback": merge_reason_feedback(structural_blocking_issues, semantic),
    }
    write_json(lgwf_dir / "step_design_observation.json", result)
    write_json(lgwf_dir / "step_designs_proposal_quality_gate.json", result)
    return result


def main() -> None:
    result = build_observation(Path.cwd())
    print(json.dumps({"lgwf_wf_create.step_design_observation": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
