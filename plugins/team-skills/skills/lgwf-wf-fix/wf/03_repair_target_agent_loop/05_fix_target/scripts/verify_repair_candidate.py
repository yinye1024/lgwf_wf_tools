from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target
from target_repair_loop import check_result, load_current_artifact, write_current_artifact

from audit_repair_changes import audit_candidate_changes
from validate_repair import validate_target_repair


def _failed_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [check for check in checks if check.get("passed") is not True and check.get("required", True)]


def _validation_failures(static_validation: dict[str, Any]) -> list[dict[str, Any]]:
    issues = static_validation.get("issues")
    return issues if isinstance(issues, list) else []


def _unexpected_changes(change_audit: dict[str, Any]) -> list[Any]:
    changes = change_audit.get("unexpected_changes")
    return changes if isinstance(changes, list) else []


def _retry_hints(
    checks: list[dict[str, Any]],
    change_audit: dict[str, Any],
    static_validation: dict[str, Any],
) -> list[str]:
    failed = {str(check.get("name")) for check in _failed_checks(checks)}
    hints: list[str] = []
    if "plan_ready" in failed:
        hints.append("重新生成修复计划，确保 plan.status=ready；如果无法自动修复，必须保留 blocked_reason。")
    if "apply_status" in failed:
        hints.append("重新执行修复计划，确保 apply.status 为 applied 或 no_changes_needed，并记录 changed_files。")
    if "change_audit" in failed:
        unexpected = _unexpected_changes(change_audit)
        hints.append(f"收敛修改范围，只修改 files_to_modify 允许的文件；当前计划外变更: {unexpected}")
    if "static_validation" in failed:
        failures = _validation_failures(static_validation)
        hints.append(f"根据静态校验失败信息修复 DSL、脚本或 Python 语法问题: {failures}")
    return hints


def _semantic_risks(
    plan: dict[str, Any],
    apply_result: dict[str, Any],
    change_audit: dict[str, Any],
) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    if plan.get("status") == "ready" and not plan.get("why_this_is_not_a_patch"):
        risks.append(
            {
                "name": "missing_root_cause_explanation",
                "risk": "计划没有说明为什么不是临时 patch，可能只是绕过当前错误文本。",
                "next_agent_action": "补充根因级修复理由，或重新规划更小且可验证的修复。",
            }
        )
    if plan.get("status") == "ready" and not plan.get("plan_steps"):
        risks.append(
            {
                "name": "missing_plan_step_mapping",
                "risk": "计划缺少 plan_steps，执行节点难以证明每个变更对应哪个修复步骤。",
                "next_agent_action": "输出结构化 plan_steps，包含 step_id、files、expected_change 和 validation。",
            }
        )
    if apply_result.get("status") == "applied" and not apply_result.get("change_details"):
        risks.append(
            {
                "name": "missing_change_details",
                "risk": "执行结果缺少逐文件变更说明，后续很难审查是否真正落实根因。",
                "next_agent_action": "补充 change_details，说明每个 changed_files 的修改内容和原因。",
            }
        )
    if apply_result.get("status") == "applied" and not apply_result.get("plan_step_results"):
        risks.append(
            {
                "name": "missing_plan_step_results",
                "risk": "执行结果没有映射计划步骤，无法判断是否按计划完成。",
                "next_agent_action": "补充 plan_step_results，逐项说明 applied、blocked 或 no_changes_needed。",
            }
        )
    missing = change_audit.get("missing_planned_changes") or []
    if missing:
        risks.append(
            {
                "name": "missing_planned_changes",
                "risk": "部分计划文件没有实际变更，可能表示计划过宽或执行遗漏。",
                "evidence": missing,
                "next_agent_action": "确认这些文件是否应移出 files_to_modify，或补齐必要修改。",
            }
        )
    return risks


def verify_candidate(
    target: dict[str, Any],
    workspace: dict[str, Any],
    plan: dict[str, Any],
    apply_result: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if plan.get("status") != "ready":
        checks.append(check_result("plan_ready", False, evidence=[f"plan.status={plan.get('status')}"]))
    else:
        checks.append(check_result("plan_ready", True))

    if apply_result.get("status") not in {"applied", "no_changes_needed"}:
        checks.append(check_result("apply_status", False, evidence=[f"apply.status={apply_result.get('status')}"]))
    else:
        checks.append(check_result("apply_status", True))

    baseline = Path(str(workspace.get("baseline_package_root") or ""))
    candidate = Path(str(workspace.get("candidate_package_root") or ""))
    if not baseline.exists() or not candidate.exists():
        change_audit = {
            "passed": False,
            "unexpected_changes": [],
            "issues": ["missing baseline or candidate package root"],
        }
    else:
        change_audit = audit_candidate_changes(baseline, candidate, plan)
    write_current_artifact(lgwf_dir(), "change_audit", change_audit)
    checks.append(
        check_result(
            "change_audit",
            change_audit.get("passed") is True,
            evidence=_unexpected_changes(change_audit) or change_audit.get("issues") or [],
        )
    )

    static_validation = validate_target_repair(target, workspace=workspace)
    checks.append(
        check_result(
            "static_validation",
            static_validation.get("passed") is True,
            evidence=_validation_failures(static_validation) or static_validation.get("commands") or [],
        )
    )

    issues = _failed_checks(checks)
    failed_checks = _failed_checks(checks)
    unexpected_changes = _unexpected_changes(change_audit)
    validation_failures = _validation_failures(static_validation)
    retry_hints = _retry_hints(checks, change_audit, static_validation)
    semantic_risks = _semantic_risks(plan, apply_result, change_audit)
    return {
        "passed": not issues,
        "checks": checks,
        "failed_checks": failed_checks,
        "issues": issues,
        "retry_hints": retry_hints,
        "unexpected_changes": unexpected_changes,
        "validation_failures": validation_failures,
        "semantic_review_needed": not issues and bool(semantic_risks),
        "semantic_risks": semantic_risks,
        "change_audit": change_audit,
        "static_validation": static_validation,
    }


def main() -> None:
    root = lgwf_dir()
    target = load_self_fix_target()
    workspace = load_current_artifact(root, "workspace", {})
    plan = load_current_artifact(root, "plan", {})
    apply_result = load_current_artifact(root, "apply", {})
    if not isinstance(workspace, dict):
        workspace = {}
    if not isinstance(plan, dict):
        plan = {}
    if not isinstance(apply_result, dict):
        apply_result = {}
    verification = verify_candidate(target, workspace, plan, apply_result)
    write_current_artifact(root, "verification", verification)
    append_history(
        {
            "event": "repair_agent_loop_verified",
            "passed": verification["passed"],
            "issues": verification["issues"],
            "semantic_review_needed": verification["semantic_review_needed"],
        }
    )
    print(json.dumps({"lgwf_wf_fix.target_repair_current_verification": verification}, ensure_ascii=False))


if __name__ == "__main__":
    main()
