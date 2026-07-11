from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from dsl_upgrade_common import ensure_runtime_dirs, load_json, write_json


def _clean_changes(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text:
            cleaned.append(text)
    return cleaned


def _load_context(root: Path) -> dict[str, Any]:
    manifest = load_json(root / ".lgwf" / "target_manifest.json", {})
    return {
        "target_manifest": manifest,
        "target_scope_validation": load_json(root / ".lgwf" / "target_scope_validation.json", {}),
        "scope_confirmation_context": load_json(root / ".lgwf" / "scope_confirmation_context.json", {}),
        "scope_approval": load_json(root / ".lgwf" / "scope_approval.json", {}),
        "request": manifest.get("request", {}) if isinstance(manifest, dict) else {},
    }


def _read_stdin_json() -> Any:
    raw = sys.stdin.read().strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _clean_target_results(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _approval_decision(scope_approval: Any) -> str:
    if not isinstance(scope_approval, dict):
        return ""
    return str(scope_approval.get("decision", "")).strip().lower()


def build_result_summary(root: Path, provided_context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = _load_context(root)
    if provided_context:
        context.update(provided_context)
    validation = context.get("target_scope_validation", {}) if isinstance(context.get("target_scope_validation", {}), dict) else {}
    manifest = context.get("target_manifest", {}) if isinstance(context.get("target_manifest", {}), dict) else {}
    request = context.get("request", {}) if isinstance(context.get("request", {}), dict) else {}
    if not request and isinstance(manifest.get("request"), dict):
        request = manifest["request"]
    scope_approval = context.get("scope_approval", {}) if isinstance(context.get("scope_approval", {}), dict) else {}
    confirm_scope_result = (
        context.get("confirm_scope_result", {}) if isinstance(context.get("confirm_scope_result", {}), dict) else {}
    )
    approval_comment = str(scope_approval.get("comment", "")).strip()
    approval_changes = _clean_changes(scope_approval.get("changes", []))
    target_results = _clean_target_results(context.get("target_results", []))
    repaired_target_count = sum(1 for item in target_results if item.get("status") == "repaired")
    passed_target_count = sum(1 for item in target_results if item.get("passed"))
    manual_target_count = sum(1 for item in target_results if item.get("status") == "needs_manual_review")
    dry_run_failed_count = sum(1 for item in target_results if item.get("status") == "dry_run_failed")
    failed_target_count = sum(1 for item in target_results if item.get("status") == "failed")
    remaining_diagnostic_count = sum(
        int(item.get("diagnostic_count", 0) or 0) for item in target_results if not item.get("passed")
    )

    mode = str(request.get("mode", "dry_run")).strip().lower()
    decision = _approval_decision(confirm_scope_result) or _approval_decision(scope_approval)
    status = "failed"
    if not validation.get("passed", False):
        status = "failed"
    elif target_results:
        if failed_target_count:
            status = "failed"
        elif manual_target_count or dry_run_failed_count:
            status = "partial"
        elif repaired_target_count:
            status = "applied"
        else:
            status = "passed"
    elif mode != "apply":
        status = "dry_run"
    elif decision != "approve":
        status = "skipped"
    else:
        status = "skipped"

    remaining_risks = []
    if validation.get("reasons"):
        remaining_risks.extend(validation["reasons"])
    if manual_target_count:
        remaining_risks.append("FOREACH 结果中仍有目标需要人工处理。")
    if dry_run_failed_count:
        remaining_risks.append("dry_run 发现未通过 audit 的目标，但未写入修复。")
    if failed_target_count:
        remaining_risks.append("FOREACH 结果中存在执行失败目标。")
    if remaining_diagnostic_count:
        remaining_risks.append("FOREACH 结果中仍有未通过 audit 的 diagnostics。")

    next_steps = []
    if status == "failed":
        next_steps.append("先处理范围校验失败或 audit 执行失败，再重新运行。")
    elif status == "dry_run":
        next_steps.append("审查 dry_run 的目标 audit 结果；如果确认可写入，再以 mode=apply 重新运行。")
    elif status == "skipped":
        if decision == "revise":
            next_steps.append("先根据审批反馈调整目标范围，再重新提交范围确认。")
        elif decision == "reject":
            next_steps.append("本次已按 reject 跳过目标修复；需要继续时重新提交 approve 决策并重跑。")
        else:
            next_steps.append("若后续允许写入，请重新提交 approve 决策并重跑 apply。")
    elif status == "partial":
        next_steps.append("复核 remaining/new findings，并决定是否扩充规则或转人工修复。")
    elif status == "passed":
        next_steps.append("所有目标 audit 已通过，未发现需要写入的修改。")
    else:
        next_steps.append("可以针对 remaining=0 的目标继续做更大范围升级批次。")

    summary = {
        "workflow_id": "wf-dsl-upgrade",
        "status": status,
        "mode": mode,
        "scope_mode": request.get("scope_mode", "explicit"),
        "approval_decision": decision or "none",
        "approval_comment": approval_comment,
        "approval_changes": approval_changes,
        "target_count": manifest.get("target_count", 0),
        "authorized_target_count": len(manifest.get("authorized_targets", [])) if isinstance(manifest.get("authorized_targets", []), list) else 0,
        "target_result_count": len(target_results),
        "repaired_target_count": repaired_target_count,
        "passed_target_count": passed_target_count,
        "manual_review_count": manual_target_count,
        "dry_run_failed_count": dry_run_failed_count,
        "failed_target_count": failed_target_count,
        "remaining_diagnostic_count": remaining_diagnostic_count,
        "target_results": target_results,
        "remaining_risks": remaining_risks,
        "next_steps": next_steps,
        "report_path": "reports/wf-dsl-upgrade/report.md",
    }
    return summary


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# wf-dsl-upgrade 执行报告",
        "",
        f"- 最终状态：`{summary['status']}`",
        f"- 模式：`{summary['mode']}`",
        f"- scope_mode：`{summary['scope_mode']}`",
        f"- 审批结论：`{summary['approval_decision']}`",
        f"- 授权目标数：`{summary['authorized_target_count']}` / `{summary['target_count']}`",
        f"- FOREACH 目标结果：`{summary['target_result_count']}`",
        f"- 已修复目标数：`{summary['repaired_target_count']}`",
        f"- audit 通过目标数：`{summary['passed_target_count']}`",
        f"- 需要人工处理目标数：`{summary['manual_review_count']}`",
        f"- dry_run 未通过目标数：`{summary['dry_run_failed_count']}`",
        f"- 执行失败目标数：`{summary['failed_target_count']}`",
        "",
        "## 审批反馈",
        "",
        f"- comment：{summary['approval_comment'] or '无'}",
    ]
    if summary["approval_changes"]:
        lines.extend([f"- change：{item}" for item in summary["approval_changes"]])
    else:
        lines.append("- change：无")
    lines.extend(["", "## FOREACH 目标结果", ""])
    if summary["target_results"]:
        for item in summary["target_results"]:
            lines.append(
                f"- `{item.get('status', 'unknown')}` {item.get('target_path', '')} "
                f"(diagnostics={item.get('diagnostic_count', 0)})"
            )
    else:
        lines.append("- 无 foreach 目标结果。")
    lines.extend(
        [
            "",
            "## 剩余诊断摘要",
            "",
            f"- remaining_diagnostics：`{summary['remaining_diagnostic_count']}`",
            "",
            "## 剩余风险",
            "",
        ]
    )
    if summary["remaining_risks"]:
        lines.extend([f"- {item}" for item in summary["remaining_risks"]])
    else:
        lines.append("- 无需额外记录的剩余风险。")
    lines.extend(
        [
            "",
            "## 建议下一步",
            "",
            *[f"- {item}" for item in summary["next_steps"]],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    root = Path.cwd()
    ensure_runtime_dirs(root)
    stdin_payload = _read_stdin_json()
    if isinstance(stdin_payload, list):
        provided_context = {"target_results": stdin_payload}
    elif isinstance(stdin_payload, dict):
        provided_context = stdin_payload
    else:
        provided_context = None
    summary = build_result_summary(root, provided_context)
    report_text = render_report(summary)
    write_json(root / ".lgwf" / "result_summary.json", summary)
    report_path = root / "reports" / "wf-dsl-upgrade" / "report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text + "\n", encoding="utf-8")
    print(json.dumps({"wf_dsl_upgrade.result_summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
