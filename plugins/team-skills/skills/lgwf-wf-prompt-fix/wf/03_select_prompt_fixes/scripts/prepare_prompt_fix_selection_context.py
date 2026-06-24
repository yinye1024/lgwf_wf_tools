from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, read_json, write_json


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _issue_id(issue: Any) -> str | None:
    if not isinstance(issue, dict):
        return None
    raw = issue.get("id")
    return raw if isinstance(raw, str) and raw else None


def _prompt_path(issue: Any) -> str:
    if not isinstance(issue, dict):
        return "<unknown>"
    raw = issue.get("prompt_path")
    return raw if isinstance(raw, str) and raw else "<unknown>"


def _issues_by_prompt_path(issues: list[Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        grouped.setdefault(_prompt_path(issue), []).append(issue)
    return grouped


def _enrich_file_result(
    file_result: dict[str, Any],
    issues_by_id: dict[str, dict[str, Any]],
    issues_by_path: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    enriched = dict(file_result)
    prompt_path = enriched.get("prompt_path") if isinstance(enriched.get("prompt_path"), str) else "<unknown>"
    issue_ids = [item for item in _safe_list(enriched.get("issue_ids")) if isinstance(item, str) and item]
    issue_map: dict[str, dict[str, Any]] = {}
    for issue_id in issue_ids:
        issue = issues_by_id.get(issue_id)
        if issue:
            issue_map[issue_id] = issue
    for issue in issues_by_path.get(prompt_path, []):
        issue_id = _issue_id(issue)
        if issue_id:
            issue_map.setdefault(issue_id, issue)
    if not issue_ids:
        issue_ids = list(issue_map)
    enriched["issue_ids"] = issue_ids
    enriched["issues"] = [issue_map[issue_id] for issue_id in issue_ids if issue_id in issue_map]
    return enriched


def _fallback_files_with_issues(issues_by_path: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    for prompt_path, path_issues in issues_by_path.items():
        issue_ids = [issue_id for issue in path_issues if (issue_id := _issue_id(issue))]
        files.append(
            {
                "prompt_path": prompt_path,
                "passed": False,
                "issue_ids": issue_ids,
                "issues": path_issues,
                "summary": "该文件存在 prompt 验收问题。",
            }
        )
    return files


def build_context(audit: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    issues = [issue for issue in _safe_list(audit.get("issues")) if isinstance(issue, dict)]
    raw_file_results = [item for item in _safe_list(audit.get("file_results")) if isinstance(item, dict)]
    issues_by_path = _issues_by_prompt_path(issues)
    issues_by_id = {issue_id: issue for issue in issues if (issue_id := _issue_id(issue))}
    file_results = [_enrich_file_result(item, issues_by_id, issues_by_path) for item in raw_file_results]
    files_with_issues = [
        item
        for item in file_results
        if not bool(item.get("passed")) or bool(item.get("issue_ids")) or bool(item.get("issues"))
    ]
    files_passed = [
        item
        for item in file_results
        if bool(item.get("passed")) and not item.get("issue_ids") and not item.get("issues")
    ]
    if not file_results:
        files_with_issues = _fallback_files_with_issues(issues_by_path)
    audit_prompt_count = audit.get("prompt_count")
    prompt_count = (
        audit_prompt_count
        if isinstance(audit_prompt_count, int) and audit_prompt_count >= 0
        else len(inventory.get("prompts", []))
        if isinstance(inventory.get("prompts"), list)
        else 0
    )
    return {
        "artifact_root": ".lgwf/prompt_acceptance",
        "audit_passed": bool(audit.get("passed")) and not issues,
        "prompt_count": prompt_count,
        "file_results": file_results,
        "files_with_issues": files_with_issues,
        "files_passed": files_passed,
        "issues_by_prompt_path": issues_by_path,
        "issues": issues,
        "instructions": {
            "fix_all": "Recommended default. Set true to repair every listed prompt issue.",
            "selected_issue_ids": "Provide a list of issue ids to repair when only part of the issues should be fixed.",
            "skip_fix": "Set true to skip prompt repair and continue.",
            "comment": "Optional operator note.",
        },
    }


def main() -> None:
    root = lgwf_dir() / "prompt_acceptance"
    audit = read_json(root / "audit.json", {})
    inventory = read_json(root / "inventory.json", {})
    if not isinstance(audit, dict):
        audit = {}
    if not isinstance(inventory, dict):
        inventory = {}
    context = build_context(audit, inventory)
    write_json(root / "selection_context.json", context)
    if not (root / "react_history.json").exists():
        write_json(root / "react_history.json", [])
    if not (root / "repair_review.json").exists():
        write_json(root / "repair_review.json", {"passed": False, "remaining_issue_ids": []})
    output_state({"prompt_fix_selection_context": context})


if __name__ == "__main__":
    main()
