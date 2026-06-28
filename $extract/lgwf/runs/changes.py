import datetime
import difflib
import hashlib
from pathlib import Path
from typing import Any

import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module

MAX_TEXT_DIFF_BYTES = 256 * 1024
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".lgwf",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}

Snapshot = dict[str, Any]
ChangeManifest = dict[str, Any]


class RunChangeError(ValueError):
    """Raised when workflow run change artifacts cannot be built."""


def capture_snapshot(
    workspace_root: Path,
    exclude_dirs: set[str] | None = None,
) -> Snapshot:
    root = workspace_root.resolve()
    if not root.is_dir():
        raise RunChangeError(f"Workspace root does not exist or is not a directory: {root}")

    excluded = DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if _is_excluded(path, root, excluded):
            continue

        relative_path = path.relative_to(root).as_posix()
        data = path.read_bytes()
        entry: dict[str, Any] = {
            "path": relative_path,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        text = _decode_text_for_diff(data)
        if text is not None:
            entry["_text"] = text
        files[relative_path] = entry

    return {
        "version": 1,
        "workspace_root": str(root),
        "generated_at": _utc_now(),
        "files": files,
    }


def build_change_manifest(
    run_id: str,
    status: str,
    workspace_root: Path,
    before: Snapshot,
    after: Snapshot,
) -> ChangeManifest:
    if not run_id:
        raise RunChangeError("run_id must be non-empty.")
    if status not in {"completed", "failed"}:
        raise RunChangeError("status must be completed or failed.")

    before_files = _snapshot_files(before)
    after_files = _snapshot_files(after)
    changed: list[dict[str, Any]] = []
    for path in sorted(set(before_files) | set(after_files)):
        before_entry = before_files.get(path)
        after_entry = after_files.get(path)
        if before_entry is not None and after_entry is not None:
            if before_entry.get("sha256") == after_entry.get("sha256"):
                continue
            change_type = "modified"
        elif before_entry is None:
            change_type = "added"
        else:
            change_type = "deleted"

        changed.append(_build_file_change(path, change_type, before_entry, after_entry))

    stats = {
        "changed_files": len(changed),
        "added": _count_change_type(changed, "added"),
        "modified": _count_change_type(changed, "modified"),
        "deleted": _count_change_type(changed, "deleted"),
        "text_files": sum(1 for item in changed if item["text"]),
        "binary_or_large_files": sum(1 for item in changed if not item["text"]),
    }
    return {
        "version": 1,
        "run_id": run_id,
        "status": status,
        "workspace_root": str(workspace_root.resolve()),
        "generated_at": _utc_now(),
        "stats": stats,
        "files": changed,
    }


def change_summary(manifest: ChangeManifest) -> dict[str, int]:
    stats = manifest.get("stats", {})
    return {
        "changed_files": int(stats.get("changed_files", 0)),
        "added": int(stats.get("added", 0)),
        "modified": int(stats.get("modified", 0)),
        "deleted": int(stats.get("deleted", 0)),
    }


def save_change_artifacts(
    workspace_root: Path,
    manifest: ChangeManifest,
    token_summary: dict[str, Any] | None = None,
    run_record: dict[str, Any] | None = None,
    run_metrics_summary: dict[str, Any] | None = None,
    failure_summary: dict[str, Any] | None = None,
) -> dict[str, Path]:
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise RunChangeError("manifest.run_id must be a non-empty string.")

    root = workspace_root.resolve()
    runs_dir = workspace_layout_module.runs_dir(root)
    file_ops_module.ensure_dir(runs_dir)
    changed_files_path = workspace_layout_module.changed_files_path(root, run_id)
    summary_path = workspace_layout_module.run_summary_path(root, run_id)
    feedback_path = workspace_layout_module.run_feedback_path(root, run_id)
    diff_path = workspace_layout_module.run_diff_path(root, run_id)

    file_ops_module.write_json_atomic(changed_files_path, _public_manifest(manifest))
    file_ops_module.write_text_atomic(
        summary_path,
        _render_summary(
            manifest,
            token_summary=token_summary,
            run_record=run_record,
            run_metrics_summary=run_metrics_summary,
            failure_summary=failure_summary,
        ),
    )
    file_ops_module.write_text_atomic(
        feedback_path,
        _render_feedback(
            manifest,
            token_summary=token_summary,
            run_record=run_record,
            run_metrics_summary=run_metrics_summary,
            failure_summary=failure_summary,
        ),
    )
    file_ops_module.write_text_atomic(diff_path, _render_diff(manifest))

    return {
        "changed_files": changed_files_path,
        "summary": summary_path,
        "feedback": feedback_path,
        "diff": diff_path,
    }


def _build_file_change(
    path: str,
    change_type: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> dict[str, Any]:
    before_text = before.get("_text") if before else None
    after_text = after.get("_text") if after else None
    is_text = isinstance(before_text, str) if after_text is None else isinstance(after_text, str)
    diff = ""
    insertions = 0
    deletions = 0
    if is_text:
        before_lines = before_text.splitlines(keepends=True) if isinstance(before_text, str) else []
        after_lines = after_text.splitlines(keepends=True) if isinstance(after_text, str) else []
        diff = "".join(
            difflib.unified_diff(
                before_lines,
                after_lines,
                fromfile=path,
                tofile=path,
                lineterm="",
            )
        )
        insertions, deletions = _count_diff_lines(diff)

    return {
        "path": path,
        "change_type": change_type,
        "text": is_text,
        "size_before": before.get("size_bytes") if before else None,
        "size_after": after.get("size_bytes") if after else None,
        "sha256_before": before.get("sha256") if before else None,
        "sha256_after": after.get("sha256") if after else None,
        "insertions": insertions,
        "deletions": deletions,
        "_diff": diff,
    }


def _render_summary(
    manifest: ChangeManifest,
    token_summary: dict[str, Any] | None = None,
    run_record: dict[str, Any] | None = None,
    run_metrics_summary: dict[str, Any] | None = None,
    failure_summary: dict[str, Any] | None = None,
) -> str:
    stats = manifest["stats"]
    lines = [
        "# LGWF Run Summary",
        "",
        f"- run_id: {manifest['run_id']}",
        f"- status: {manifest['status']}",
        f"- workspace_root: {manifest['workspace_root']}",
        f"- changed_files: {stats['changed_files']}",
        f"- added: {stats['added']}",
        f"- modified: {stats['modified']}",
        f"- deleted: {stats['deleted']}",
    ]
    lines.extend(_render_run_timing(run_record))
    lines.extend(_render_node_timeline(run_metrics_summary))
    lines.extend(_render_warning_summary(run_metrics_summary))
    lines.extend(_render_final_artifacts(manifest))
    lines.extend(_render_failure_summary(failure_summary))
    lines.extend(["", "## Changed Files", ""])
    if not manifest["files"]:
        lines.append("- 无文件改动。")
    for item in manifest["files"]:
        lines.append(
            f"- `{item['path']}` ({item['change_type']}, +{item['insertions']}/-{item['deletions']})"
        )
    lines.extend(_render_token_summary(token_summary))
    lines.append("")
    lines.append(f"Diff: `{manifest['run_id']}.diff.patch`")
    return "\n".join(lines) + "\n"


def _render_feedback(
    manifest: ChangeManifest,
    token_summary: dict[str, Any] | None = None,
    run_record: dict[str, Any] | None = None,
    run_metrics_summary: dict[str, Any] | None = None,
    failure_summary: dict[str, Any] | None = None,
) -> str:
    lines = [
        "# LGWF 运行反馈",
        "",
        "## 运行状态",
        "",
        f"- 状态：{manifest['status']}",
        f"- run_id：`{manifest['run_id']}`",
        f"- workflow：`{_workflow_label(run_record)}`",
        f"- workspace：`{manifest['workspace_root']}`",
    ]
    lines.extend(_render_run_timing(run_record, chinese=True))
    lines.extend(_render_approval_summary(run_metrics_summary))
    lines.extend(_render_react_statuses(run_metrics_summary))
    lines.extend(_render_slow_nodes(run_metrics_summary))
    lines.extend(_render_failure_signals(run_metrics_summary))
    lines.extend(_render_warning_summary(run_metrics_summary, chinese=True))
    lines.extend(_render_final_artifacts(manifest, run_metrics_summary, chinese=True))
    lines.extend(_render_failure_summary(failure_summary))
    lines.extend(_render_token_summary(token_summary))
    lines.append("")
    lines.append(f"- Summary：`{manifest['run_id']}.summary.md`")
    lines.append(f"- Diff：`{manifest['run_id']}.diff.patch`")
    return "\n".join(lines) + "\n"


def _render_run_timing(run_record: dict[str, Any] | None, chinese: bool = False) -> list[str]:
    if not isinstance(run_record, dict):
        return []
    started_at = run_record.get("started_at")
    finished_at = run_record.get("finished_at")
    duration_ms = _duration_ms(started_at, finished_at)
    title = "## 运行耗时" if chinese else "## Run Timing"
    started_label = "开始" if chinese else "started_at"
    finished_label = "结束" if chinese else "finished_at"
    duration_label = "总耗时" if chinese else "duration_ms"
    return [
        "",
        title,
        "",
        f"- {started_label}: `{started_at or '<unknown>'}`",
        f"- {finished_label}: `{finished_at or '<unknown>'}`",
        f"- {duration_label}: {duration_ms if duration_ms is not None else 'unknown'} ms",
    ]


def _render_node_timeline(run_metrics_summary: dict[str, Any] | None) -> list[str]:
    nodes = _metric_nodes(run_metrics_summary)
    if not nodes:
        return []
    lines = ["", "## Node Timeline", ""]
    for item in nodes:
        lines.append(
            "- "
            f"`{item.get('node_id')}` capability=`{item.get('capability')}` "
            f"duration_ms={item.get('duration_ms')} ok={item.get('ok')} "
            f"exit_code={item.get('exit_code')} warnings={item.get('warning_count', 0)}"
        )
    lines.extend(_render_slow_nodes(run_metrics_summary, chinese=False))
    return lines


def _render_slow_nodes(run_metrics_summary: dict[str, Any] | None, chinese: bool = True) -> list[str]:
    nodes = _metric_slow_nodes(run_metrics_summary)
    title = "## 慢节点排行" if chinese else "## Slow Nodes"
    lines = ["", title, ""]
    if not nodes:
        lines.append("- 无节点耗时数据。")
        return lines
    for item in nodes[:10]:
        lines.append(
            f"- `{item.get('node_id')}` {item.get('duration_ms')} ms capability=`{item.get('capability')}`"
        )
    return lines


def _render_approval_summary(run_metrics_summary: dict[str, Any] | None) -> list[str]:
    approvals = []
    if isinstance(run_metrics_summary, dict) and isinstance(run_metrics_summary.get("approvals"), list):
        approvals = run_metrics_summary["approvals"]
    lines = ["", "## Human Approval", ""]
    if not approvals:
        lines.append("- 本次运行没有 human approval 节点，或没有捕获到 approval 摘要。")
        return lines
    for item in approvals:
        lines.append(
            f"- `{item.get('node_id')}` decision={item.get('decision')} "
            f"request_id=`{item.get('request_id')}` wait_ms={item.get('duration_ms')}"
        )
    return lines


def _render_react_statuses(run_metrics_summary: dict[str, Any] | None) -> list[str]:
    statuses = []
    if isinstance(run_metrics_summary, dict) and isinstance(run_metrics_summary.get("react_statuses"), list):
        statuses = run_metrics_summary["react_statuses"]
    lines = ["", "## React 状态", ""]
    if not statuses:
        lines.append("- 无 react 状态摘要。")
        return lines
    for item in statuses:
        lines.append(
            "- "
            f"`{item.get('node_id')}` state=`{item.get('state_path')}` "
            f"exit_reason={item.get('exit_reason')} rounds={item.get('rounds')} "
            f"continuations={item.get('continuations')} max_steps={item.get('max_steps')}"
        )
    return lines


def _render_warning_summary(run_metrics_summary: dict[str, Any] | None, chinese: bool = False) -> list[str]:
    warnings = []
    if isinstance(run_metrics_summary, dict) and isinstance(run_metrics_summary.get("warnings"), list):
        warnings = run_metrics_summary["warnings"]
    title = "## Stderr Warning" if not chinese else "## Stderr Warning 摘要"
    lines = ["", title, ""]
    if not warnings:
        lines.append("- 无 stderr warning。")
        return lines
    for item in warnings:
        preview = item.get("stderr_preview")
        preview_text = " | ".join(preview) if isinstance(preview, list) else ""
        lines.append(
            "- "
            f"`{item.get('node_id')}` state=`{item.get('state_path')}` "
            f"stderr_size={item.get('stderr_size')} stderr_path=`{item.get('stderr_path') or '<unavailable>'}`"
        )
        if preview_text:
            lines.append(f"  - preview: {preview_text}")
    return lines


def _render_failure_signals(run_metrics_summary: dict[str, Any] | None) -> list[str]:
    signals = []
    if isinstance(run_metrics_summary, dict) and isinstance(run_metrics_summary.get("failure_signals"), list):
        signals = run_metrics_summary["failure_signals"]
    lines = ["", "## 失败/异常信号", ""]
    if not signals:
        lines.append("- 无 collect-mode 子步骤失败或其他异常信号。")
        return lines
    for item in signals:
        lines.append(
            "- "
            f"`{item.get('node_id')}` state=`{item.get('state_path')}` "
            f"error_type={item.get('error_type')} message={item.get('message')}"
        )
    return lines


def _render_final_artifacts(
    manifest: ChangeManifest,
    run_metrics_summary: dict[str, Any] | None = None,
    chinese: bool = False,
) -> list[str]:
    title = "## 最终产物" if chinese else "## Final Artifacts"
    lines = ["", title, ""]
    artifact_paths = _execution_artifact_paths(run_metrics_summary)
    artifact_paths.extend(
        item["path"]
        for item in manifest.get("files", [])
        if item.get("change_type") in {"added", "modified"}
        and _looks_like_report_artifact(str(item.get("path", "")))
    )
    artifact_paths = sorted(dict.fromkeys(path for path in artifact_paths if path))
    if not artifact_paths:
        lines.append("- 未识别到最终报告产物。")
        return lines
    for path in artifact_paths:
        lines.append(f"- `{path}`")
    return lines


def _execution_artifact_paths(run_metrics_summary: dict[str, Any] | None) -> list[str]:
    if not isinstance(run_metrics_summary, dict):
        return []
    artifacts = run_metrics_summary.get("artifacts")
    if not isinstance(artifacts, list):
        return []
    result = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if isinstance(path, str) and path:
            result.append(path)
    return result


def _looks_like_report_artifact(path: str) -> bool:
    if not path:
        return False
    return (
        path.startswith("reports/")
        and path.endswith((".md", ".json", ".html", ".txt"))
    ) or path.endswith((".summary.md", ".feedback.md"))


def _workflow_label(run_record: dict[str, Any] | None) -> str:
    if not isinstance(run_record, dict):
        return "<unknown>"
    workflow = run_record.get("workflow")
    if not isinstance(workflow, dict):
        return "<unknown>"
    source = workflow.get("source") or "<unknown>"
    name = workflow.get("name") or "<unknown>"
    version = workflow.get("version")
    if version:
        return f"{source}/{name}@{version}"
    return f"{source}/{name}"


def _duration_ms(started_at: Any, finished_at: Any) -> int | None:
    if not isinstance(started_at, str) or not isinstance(finished_at, str):
        return None
    try:
        started = datetime.datetime.fromisoformat(started_at)
        finished = datetime.datetime.fromisoformat(finished_at)
    except ValueError:
        return None
    return int((finished - started).total_seconds() * 1000)


def _metric_nodes(run_metrics_summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(run_metrics_summary, dict):
        return []
    nodes = run_metrics_summary.get("nodes")
    return nodes if isinstance(nodes, list) else []


def _metric_slow_nodes(run_metrics_summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(run_metrics_summary, dict):
        return []
    nodes = run_metrics_summary.get("slow_nodes")
    return nodes if isinstance(nodes, list) else []


def _render_failure_summary(failure_summary: dict[str, Any] | None) -> list[str]:
    if not failure_summary:
        return []
    return [
        "",
        "## Failure Summary",
        "",
        f"- node_id: `{failure_summary.get('node_id') or '<unknown>'}`",
        f"- capability: `{failure_summary.get('capability') or '<unknown>'}`",
        f"- error_type: `{failure_summary.get('error_type') or '<unknown>'}`",
        f"- message: {failure_summary.get('message') or ''}",
    ]


def _render_token_summary(token_summary: dict[str, Any] | None) -> list[str]:
    if not token_summary:
        return ["", "## Token Usage", "", "- token usage unavailable"]
    steps = token_summary.get("steps")
    totals = token_summary.get("totals")
    if not isinstance(steps, list) or not isinstance(totals, dict):
        return []

    lines = [
        "",
        "## Token Usage",
        "",
    ]
    if not steps:
        lines.append("- token usage unavailable")
        return lines

    lines.extend(
        [
            f"- total_tokens: {_int_value(totals.get('total_tokens'))}",
            f"- input_tokens: {_int_value(totals.get('input_tokens'))}",
            f"- output_tokens: {_int_value(totals.get('output_tokens'))}",
            f"- cached_input_tokens: {_int_value(totals.get('cached_input_tokens'))}",
            f"- reasoning_output_tokens: {_int_value(totals.get('reasoning_output_tokens'))}",
            "",
            "### By Step",
            "",
        ]
    )
    for item in steps:
        if not isinstance(item, dict):
            continue
        usage = item.get("token_usage")
        if not isinstance(usage, dict):
            continue
        lines.append(
            "- "
            f"`{item.get('node_id')}` "
            f"state=`{item.get('state_path')}` "
            f"total={_int_value(usage.get('total_tokens'))} "
            f"input={_int_value(usage.get('input_tokens'))} "
            f"output={_int_value(usage.get('output_tokens'))} "
            f"cached={_int_value(usage.get('cached_input_tokens'))} "
            f"reasoning={_int_value(usage.get('reasoning_output_tokens'))}"
        )
    return lines


def _int_value(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _render_diff(manifest: ChangeManifest) -> str:
    parts = [item.get("_diff", "") for item in manifest["files"] if item.get("_diff")]
    if not parts:
        return ""
    return "\n".join(parts)


def _public_manifest(manifest: ChangeManifest) -> ChangeManifest:
    files = []
    for item in manifest["files"]:
        public_item = {key: value for key, value in item.items() if not key.startswith("_")}
        files.append(public_item)
    public = dict(manifest)
    public["files"] = files
    return public


def _snapshot_files(snapshot: Snapshot) -> dict[str, dict[str, Any]]:
    files = snapshot.get("files")
    if not isinstance(files, dict):
        raise RunChangeError("snapshot.files must be an object.")
    return files


def _decode_text_for_diff(data: bytes) -> str | None:
    if len(data) > MAX_TEXT_DIFF_BYTES or b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _count_diff_lines(diff: str) -> tuple[int, int]:
    insertions = 0
    deletions = 0
    for line in diff.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+"):
            insertions += 1
        elif line.startswith("-"):
            deletions += 1
    return insertions, deletions


def _count_change_type(items: list[dict[str, Any]], change_type: str) -> int:
    return sum(1 for item in items if item["change_type"] == change_type)


def _is_excluded(path: Path, root: Path, exclude_dirs: set[str]) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in exclude_dirs for part in relative_parts[:-1])


def _utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()

