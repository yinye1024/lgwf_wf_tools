from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from _paths import FACADE_ROOT, SELF_IMPROVE_ROOT
DEFAULT_OUTPUT_DIR = FACADE_ROOT / ".local" / "self-improve" / "proposals"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def find_workflow_result(report: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    results = report.get("workflow_results")
    if not isinstance(results, list):
        raise ValueError("health report missing workflow_results")
    for item in results:
        if isinstance(item, dict) and item.get("id") == workflow_id:
            return item
    raise ValueError(f"workflow id not found in health report: {workflow_id}")


def read_changed_files(path: Path | None) -> list[str]:
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError("--changed-files must point to a JSON string array")
    return data


def failed_eval_cases(eval_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not eval_report:
        return []
    cases = eval_report.get("case_results", [])
    if not isinstance(cases, list):
        return []
    return [item for item in cases if isinstance(item, dict) and not item.get("passed")]


def failed_trace_eval_checks(trace_eval_report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not trace_eval_report:
        return []
    checks = trace_eval_report.get("failed_checks", [])
    if not isinstance(checks, list):
        return []
    return [item for item in checks if isinstance(item, dict)]


def candidate_files(workflow_id: str, workflow_result: dict[str, Any], changed_files: list[str]) -> list[str]:
    root = workflow_result.get("workflow_root")
    candidates: list[str] = []
    if isinstance(root, str) and root:
        candidates.extend(
            [
                f"{root}/AGENTS.md",
                f"{root}/workflow.lgwf",
                f"{root}/tests/",
            ]
        )
    candidates.extend(path for path in changed_files if workflow_id in path)
    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def render_proposal(
    workflow_id: str,
    health_report_path: Path,
    workflow_result: dict[str, Any],
    incident: dict[str, Any] | None,
    eval_report: dict[str, Any] | None,
    trace_eval_report: dict[str, Any] | None,
    changed_files: list[str],
) -> str:
    issues = workflow_result.get("issues") or []
    baseline = workflow_result.get("baseline") if isinstance(workflow_result.get("baseline"), dict) else {}
    failed_cases = failed_eval_cases(eval_report)
    trace_failed_checks = failed_trace_eval_checks(trace_eval_report)
    candidates = candidate_files(workflow_id, workflow_result, changed_files)
    needs_approval = bool(issues or incident or failed_cases or trace_failed_checks)
    lines = [
        f"# Workflow Improvement Proposal: {workflow_id}",
        "",
        "## 问题证据",
        "",
        f"- health_report: `{health_report_path}`",
        f"- workflow_passed: `{workflow_result.get('passed')}`",
        f"- expected_role: {baseline.get('expected_role', '')}",
        f"- changed_files: `{len(changed_files)}`",
        "",
        "## Health Issues",
        "",
    ]
    if issues:
        lines.extend(f"- {issue}" for issue in issues)
    else:
        lines.append("- 当前 health check 未发现确定性问题；请结合 incident 做人工复核。")
    if incident:
        lines.extend(
            [
                "",
                "## Incident",
                "",
                f"- id: `{incident.get('id', '')}`",
                f"- type: `{incident.get('type', '')}`",
                f"- severity: `{incident.get('severity', '')}`",
                f"- summary: {incident.get('summary', '')}",
            ]
        )
    if failed_cases:
        lines.extend(["", "## Eval Failures", ""])
        for case in failed_cases:
            lines.append(f"- `{case.get('id', '')}`: {case.get('issues', [])}")
    if trace_eval_report:
        lines.extend(
            [
                "",
                "## Trace Eval Evidence",
                "",
                f"- trace_eval_passed: `{trace_eval_report.get('passed')}`",
                f"- run_id: `{trace_eval_report.get('run_id', '')}`",
                f"- trace_path: `{trace_eval_report.get('trace_path', '')}`",
                f"- eval_suite_path: `{trace_eval_report.get('eval_suite_path', '')}`",
            ]
        )
        if trace_failed_checks:
            for check in trace_failed_checks:
                lines.append(
                    "- "
                    f"case `{check.get('case_id', '')}` check `{check.get('check_name', '')}`: "
                    f"{check.get('message', '')}"
                )
                lines.append(
                    "  - "
                    f"node `{check.get('node_id')}` capability `{check.get('capability')}` "
                    f"route `{check.get('route')}` client_call `{check.get('client_call_id')}`"
                )
                lines.append(
                    "  - "
                    f"destructive `{check.get('involves_destructive')}` "
                    f"forbidden_permission `{check.get('involves_forbidden_permission')}` "
                    f"unexpected_route `{check.get('involves_unexpected_route')}`"
                )
        else:
            lines.append("- 当前 trace eval 未发现失败 check。")
    lines.extend(
        [
            "",
            "## 影响范围",
            "",
            f"- workflow_id: `{workflow_id}`",
            f"- workflow_root: `{workflow_result.get('workflow_root', '')}`",
            "- 影响面限定在该内部 workflow 的职责、指引、测试和 proposal，不自动修改 facade 核心规则。",
            "",
            "## 推荐修改文件",
            "",
        ]
    )
    if candidates:
        lines.extend(f"- `{item}`" for item in candidates)
    else:
        lines.append("- 需要人工根据 health issue 选择候选文件。")
    lines.extend(
        [
            "- 不修改：`vendor/`、`.local/` 历史、其他 workflow，除非用户另行批准。",
            "",
            "## 验收命令",
            "",
            f"- `{baseline.get('audit_command', '')}`",
            f"- `{baseline.get('test_command', '')}`",
            "- `python workflows/self-improve/scripts/check_workflow_health.py --workflow-id " + workflow_id + "`",
            "",
            "## 是否需要用户 approval",
            "",
            f"- `{str(needs_approval).lower()}`",
            "- 原因：该 proposal 只提出修改建议；进入实际修改、promote 或影响 workflow 行为前必须由用户确认。",
            "",
            "## 决策",
            "",
            "- `approve`: 允许进入普通修改流程。",
            "- `reject`: 不应用修改，只保留 proposal。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument("--health-report", required=True)
    parser.add_argument("--incident")
    parser.add_argument("--eval-report")
    parser.add_argument("--trace-eval-report")
    parser.add_argument("--changed-files")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    health_report_path = Path(args.health_report)
    health_report = read_json(health_report_path)
    incident = read_json(Path(args.incident)) if args.incident else None
    eval_report = read_json(Path(args.eval_report)) if args.eval_report else None
    trace_eval_report = read_json(Path(args.trace_eval_report)) if args.trace_eval_report else None
    changed_files = read_changed_files(Path(args.changed_files)) if args.changed_files else []
    workflow_result = find_workflow_result(health_report, args.workflow_id)
    output = Path(args.output_dir) / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-workflow-{args.workflow_id}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        render_proposal(
            args.workflow_id,
            health_report_path,
            workflow_result,
            incident,
            eval_report,
            trace_eval_report,
            changed_files,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"proposal": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
