from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from prompt_fix_common import lgwf_dir, output_state, read_json, write_json


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_review_context(selection_context: dict[str, Any]) -> dict[str, Any]:
    issues = [item for item in _safe_list(selection_context.get("issues")) if isinstance(item, dict)]
    has_issues = bool(issues)
    return {
        "artifact_root": ".lgwf/prompt_acceptance",
        "review_kind": "prompt_fix_selection",
        "source_context_file": ".lgwf/prompt_acceptance/selection_context.json",
        "review_control_file": ".lgwf/prompt_acceptance/fix_selection_review.json",
        "final_selection_file": ".lgwf/prompt_acceptance/fix_selection.json",
        "audit_passed": bool(selection_context.get("audit_passed")) and not has_issues,
        "prompt_count": selection_context.get("prompt_count", 0),
        "file_results": _safe_list(selection_context.get("file_results")),
        "files_with_issues": _safe_list(selection_context.get("files_with_issues")),
        "files_passed": _safe_list(selection_context.get("files_passed")),
        "issues_by_prompt_path": (
            selection_context.get("issues_by_prompt_path")
            if isinstance(selection_context.get("issues_by_prompt_path"), dict)
            else {}
        ),
        "issues": issues,
        "fix_all": has_issues,
        "selected_issue_ids": [],
        "skip_fix": not has_issues,
        "comment": "",
        "instructions": {
            "approve": "确认当前 JSON；approve 不提交业务 value。",
            "revise": "提交完整更新后的 JSON object，不能提交局部 patch。",
            "reject": "停止 prompt 修复选择流程。",
            "fix_all": "true 表示修复 issues 中的全部问题。",
            "selected_issue_ids": "仅部分修复时填写 issues[].id。",
            "skip_fix": "true 表示不进入自动修复，后续只生成摘要。",
            "comment": "可选操作说明。",
        },
    }


def main() -> None:
    root = lgwf_dir() / "prompt_acceptance"
    selection_context = read_json(root / "selection_context.json", {})
    if not isinstance(selection_context, dict):
        selection_context = {}
    review_context = build_review_context(selection_context)
    write_json(root / "fix_selection_review_context.json", review_context)
    output_state({"prompt_fix_selection_review_context": review_context})


if __name__ == "__main__":
    main()
