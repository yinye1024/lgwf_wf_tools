from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _paths import LOCAL_SELF_IMPROVE


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "proposal"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def default_trace_eval_report() -> dict[str, Any] | None:
    path = LOCAL_SELF_IMPROVE / "reports" / "latest-trace-eval.json"
    return read_json(path) if path.is_file() else None


def trace_failed_checks(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []
    checks = report.get("failed_checks", [])
    return [item for item in checks if isinstance(item, dict)] if isinstance(checks, list) else []


def render_trace_eval(report: dict[str, Any] | None) -> list[str]:
    if not report:
        return ["- trace_eval_report: `not_found`"]
    lines = [
        f"- trace_eval_passed: `{report.get('passed')}`",
        f"- run_id: `{report.get('run_id', '')}`",
        f"- trace_path: `{report.get('trace_path', '')}`",
        f"- eval_suite_path: `{report.get('eval_suite_path', '')}`",
    ]
    failed = trace_failed_checks(report)
    if not failed:
        lines.append("- 当前 trace eval 未发现失败 check。")
        return lines
    for check in failed:
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
    return lines


def render_proposal(topic: str, source_path: Path, source: dict[str, Any], trace_eval_report: dict[str, Any] | None) -> str:
    summary = source.get("summary") or source.get("id") or topic
    lines = [
        f"# Self Improve Proposal: {topic}",
        "",
        "## 证据",
        "",
        f"- source_path: `{source_path}`",
        f"- summary: {summary}",
        "",
        "## Trace Eval Evidence",
        "",
        *render_trace_eval(trace_eval_report),
        "",
        "## 根因判断",
        "",
        f"- suspected_area: `{source.get('suspected_area', 'unknown')}`",
        "- 需要人工复核具体根因；本文件只作为提案起点。",
        "",
        "## 拟修改范围",
        "",
        "- 候选文件：目标 workflow 的 `AGENTS.md`、`wf/**`、测试或 self-improve eval case。",
        "- 不自动修改业务文件；执行前必须由用户明确批准。",
        "",
        "## 验证方式",
        "",
        "- `python self-improve/scripts/self_improve.py check`",
        "- `python self-improve/scripts/self_improve.py trace-eval`",
        "- 如涉及运行行为，补充目标 workflow 自己的测试或审计命令。",
        "",
        "## 决策",
        "",
        "- `approve`: 允许按本 proposal 进入普通修改流程。",
        "- `reject`: 不应用修改，只保留记录。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident", required=True)
    parser.add_argument("--topic")
    parser.add_argument("--trace-eval-report")
    args = parser.parse_args()

    source_path = Path(args.incident)
    source = read_json(source_path)
    trace_eval_report = read_json(Path(args.trace_eval_report)) if args.trace_eval_report else default_trace_eval_report()
    topic = args.topic or str(source.get("summary") or source.get("id") or "self-improve")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output = LOCAL_SELF_IMPROVE / "proposals" / f"{stamp}-{slugify(topic)}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_proposal(topic, source_path, source, trace_eval_report), encoding="utf-8")
    print(json.dumps({"proposal": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
