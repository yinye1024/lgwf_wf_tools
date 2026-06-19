from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state, read_json, read_text, write_json


def _parse_json_maybe(value: Any) -> Any:
    if not isinstance(value, str) or not value.strip():
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _history_times(history: list[Any]) -> tuple[str | None, str | None, int | None]:
    stamps: list[datetime] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        raw = item.get("ts") or item.get("timestamp") or item.get("time")
        if not isinstance(raw, str):
            continue
        try:
            stamps.append(datetime.fromisoformat(raw.replace("Z", "+00:00")))
        except ValueError:
            continue
    if not stamps:
        return None, None, None
    started = min(stamps)
    finished = max(stamps)
    return started.isoformat(), finished.isoformat(), int((finished - started).total_seconds())


def _collect_changed_files(value: Any) -> list[str]:
    files: set[str] = set()
    parsed = _parse_json_maybe(value)
    for item in _walk(parsed):
        for key in ("changed_files", "files", "modified_files"):
            raw = item.get(key)
            if isinstance(raw, list):
                for path in raw:
                    if isinstance(path, str) and path:
                        files.add(path)
        path = item.get("path") or item.get("file")
        if isinstance(path, str) and path:
            files.add(path)
    return sorted(files)


def _collect_token_usage(value: Any) -> dict[str, int]:
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    parsed = _parse_json_maybe(value)
    for item in _walk(parsed):
        for key in tuple(usage):
            raw = item.get(key)
            if isinstance(raw, int):
                usage[key] += raw
    return {key: value for key, value in usage.items() if value}


def _collect_issues(failure_review: dict[str, Any]) -> list[dict[str, Any]]:
    if not failure_review:
        return []
    status = failure_review.get("status") if isinstance(failure_review.get("status"), dict) else {}
    error = failure_review.get("error") or failure_review.get("stderr") or status.get("last_error")
    issue = {
        "attempt": failure_review.get("attempt"),
        "phase": failure_review.get("phase"),
        "error": error,
        "work_dir": failure_review.get("work_dir"),
    }
    return [{key: value for key, value in issue.items() if value is not None}]


def _collect_fixes(history: list[Any], fix_notes: str) -> list[str]:
    fixes: list[str] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        if item.get("event") == "fix_attempt_recorded":
            notes = item.get("notes")
            if isinstance(notes, str) and notes.strip():
                fixes.append(notes.strip())
    if fix_notes.strip() and fix_notes.strip() not in fixes:
        fixes.append(fix_notes.strip())
    return fixes


def build_summary(
    *,
    target: dict[str, Any],
    history: list[Any],
    failure_review: dict[str, Any],
    fix_notes: str,
) -> dict[str, Any]:
    started_at, finished_at, duration_seconds = _history_times(history)
    artifacts = failure_review.get("run_artifacts") if isinstance(failure_review.get("run_artifacts"), dict) else {}
    changed_files = _collect_changed_files(artifacts.get("changed_stdout")) + _collect_changed_files(failure_review)
    token_usage = _collect_token_usage(artifacts.get("summary_stdout"))
    if not token_usage:
        token_usage = _collect_token_usage(failure_review)
    status = "success" if target.get("last_status") == "succeeded" else "failed"
    return {
        "target_workflow": target.get("target_workflow_lgwf"),
        "status": status,
        "attempts": target.get("current_attempt", 0),
        "max_attempts": target.get("max_attempts", 5),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "token_usage": token_usage,
        "issues_found": _collect_issues(failure_review),
        "fixes_applied": _collect_fixes(history, fix_notes),
        "changed_files": sorted(set(changed_files)),
        "history_events": history,
    }


def _format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    minutes, remaining = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {remaining}s"
    if minutes:
        return f"{minutes}m {remaining}s"
    return f"{remaining}s"


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# LGWF Workflow Self Fix Summary",
        "",
        f"- Target workflow: `{summary.get('target_workflow')}`",
        f"- Status: {summary.get('status')}",
        f"- Attempts: {summary.get('attempts')} / {summary.get('max_attempts')}",
        f"- Duration: {_format_duration(summary.get('duration_seconds'))}",
        f"- Token usage: `{json.dumps(summary.get('token_usage') or {}, ensure_ascii=False)}`",
        "",
        "## Issues Found",
    ]
    issues = summary.get("issues_found") or []
    if issues:
        for issue in issues:
            lines.append(f"- `{issue.get('phase', 'unknown')}`: {issue.get('error', 'unknown error')}")
    else:
        lines.append("- None recorded.")
    lines.extend(["", "## Fixes Applied"])
    fixes = summary.get("fixes_applied") or []
    if fixes:
        for fix in fixes:
            lines.append(f"- {fix}")
    else:
        lines.append("- None recorded.")
    lines.extend(["", "## Changed Files"])
    files = summary.get("changed_files") or []
    if files:
        for path in files:
            lines.append(f"- `{path}`")
    else:
        lines.append("- None recorded.")
    lines.extend(["", "## History"])
    for item in summary.get("history_events") or []:
        lines.append(f"- `{json.dumps(item, ensure_ascii=False)}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    root = Path.cwd()
    lgwf = lgwf_dir()
    target = load_self_fix_target()
    history = read_json(lgwf / "self_fix_history.json", [])
    if not isinstance(history, list):
        history = []
    failure_review = read_json(lgwf / "target_failure_review.json", {})
    if not isinstance(failure_review, dict):
        failure_review = {}
    summary = build_summary(
        target=target,
        history=history,
        failure_review=failure_review,
        fix_notes=read_text(lgwf / "target_fix_notes.md", limit=20000),
    )
    write_json(lgwf / "self_fix_summary.json", summary)
    report_dir = root / "reports" / "lgwf-wf-self-fix"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / "final_report.md"
    report.write_text(render_markdown(summary), encoding="utf-8")
    append_history({"event": "summary_written", "report": str(report), "summary": str(lgwf / "self_fix_summary.json")})
    output_state({"summary": summary, "final_report": str(report), "summary_path": str(lgwf / "self_fix_summary.json")})


if __name__ == "__main__":
    main()
