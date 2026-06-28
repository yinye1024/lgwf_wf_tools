from pathlib import Path
from collections.abc import Callable
import datetime
from typing import Any

import lgwf.compiler.dsl as compiler_module
import lgwf.progress as progress_module
import lgwf.runs.changes as run_changes_module
import lgwf.runs.metrics as run_metrics_module
import lgwf.runs.records as run_records_module
import lgwf.runtime_context as runtime_context_module
import lgwf_tools.timing as timing_module
import lgwf.workflows.registry as workflow_registry_module


RuntimeResult = dict[str, Any]


def invoke_dsl(
    dsl: dict[str, Any],
    input_state: dict[str, Any],
    workspace_root: Path | None = None,
    record: bool = True,
    progress_writer: Callable[[str], None] | None = None,
    run_id: str | None = None,
    workflow_root: Path | None = None,
) -> RuntimeResult:
    return _invoke_dsl_with_record(
        dsl=dsl,
        input_state=input_state,
        workflow_root=workflow_root,
        workspace_root=workspace_root,
        record=record,
        workflow_source="dynamic",
        workflow_name="external",
        workflow_version=None,
        progress_writer=progress_writer,
        run_id=run_id,
    )


def invoke_workflow(
    input_state: dict[str, Any],
    workflow_name: str | None = None,
    workflow_version: str | None = None,
    workspace_root: Path | None = None,
    record: bool = True,
    progress_writer: Callable[[str], None] | None = None,
    run_id: str | None = None,
) -> RuntimeResult:
    entry = workflow_registry_module.resolve_workflow(
        name=workflow_name,
        version=workflow_version,
    )
    dsl = workflow_registry_module.load_workflow_dsl(
        name=entry["name"],
        version=entry["version"],
    )
    return _invoke_dsl_with_record(
        dsl=dsl,
        input_state=input_state,
        workflow_root=None,
        workspace_root=workspace_root,
        record=record,
        workflow_source="registry",
        workflow_name=entry["name"],
        workflow_version=entry["version"],
        progress_writer=progress_writer,
        run_id=run_id,
    )


def _invoke_dsl_with_record(
    dsl: dict[str, Any],
    input_state: dict[str, Any],
    workflow_root: Path | None,
    workspace_root: Path | None,
    record: bool,
    workflow_source: str,
    workflow_name: str,
    workflow_version: str | None,
    progress_writer: Callable[[str], None] | None,
    run_id: str | None,
) -> RuntimeResult:
    effective_run_id = run_id or run_records_module.new_run_id()
    compile_timer = timing_module.Timer.start()
    with progress_module.use_run_id(effective_run_id):
        graph = compiler_module.compile_dsl(dsl)
        _emit_workflow_timing(
            progress_writer,
            f"[workflow] startup step=compile_dsl duration_ms={compile_timer.elapsed_ms()}",
            effective_run_id,
        )
    resolved_workspace_root = (workspace_root or Path(".")).resolve()
    snapshot_timer = timing_module.Timer.start()
    before_snapshot = run_changes_module.capture_snapshot(resolved_workspace_root) if record else None
    if record:
        _emit_workflow_timing(
            progress_writer,
            f"[workflow] startup step=capture_before_snapshot duration_ms={snapshot_timer.elapsed_ms()}",
            effective_run_id,
        )
    run_metrics: list[run_metrics_module.RunMetrics] | None = None
    run_started_at = _utc_now()
    with progress_module.capture_failures():
        try:
            with run_metrics_module.collect_run_metrics(record) as collected_metrics:
                run_metrics = collected_metrics
                with runtime_context_module.use_work_dir_root(resolved_workspace_root):
                    with runtime_context_module.use_workspace_root(resolved_workspace_root):
                        with runtime_context_module.use_workflow_root(workflow_root):
                            with progress_module.use_progress_writer(progress_writer):
                                with progress_module.use_run_id(effective_run_id):
                                    execute_timer = timing_module.Timer.start()
                                    final_state = graph.invoke(input_state)
                                    progress_module.emit(
                                        f"[workflow] execution duration_ms={execute_timer.elapsed_ms()}"
                                    )
        except Exception as exc:
            failure_summary = _failure_summary(exc)
            _emit_workflow_failed(
                progress_writer,
                "[workflow] failed "
                f"node={failure_summary.get('node_id') or '<unknown>'} "
                f"capability={failure_summary.get('capability') or '<unknown>'} "
                f"error={failure_summary['error_type']}: {failure_summary['message']}",
                effective_run_id,
            )
            if record and before_snapshot is not None:
                _record_run_artifacts(
                    workspace_root=resolved_workspace_root,
                    workflow_name=workflow_name,
                    workflow_version=workflow_version,
                    input_state=input_state,
                    final_state={"__lgwf_failure__": failure_summary},
                    status="failed",
                    workflow_source=workflow_source,
                    dsl_summary=_dsl_summary(dsl),
                    before_snapshot=before_snapshot,
                    token_summary=run_metrics_module.token_summary(run_metrics),
                    run_metrics_summary=run_metrics_module.run_summary(run_metrics),
                    failure_summary=failure_summary,
                    started_at=run_started_at,
                    finished_at=_utc_now(),
                    run_id=effective_run_id,
                )
            raise

    if record:
        _record_run_artifacts(
            workspace_root=resolved_workspace_root,
            workflow_name=workflow_name,
            workflow_version=workflow_version,
            input_state=input_state,
            final_state=final_state,
            status="completed",
            workflow_source=workflow_source,
            dsl_summary=_dsl_summary(dsl),
            before_snapshot=before_snapshot,
            token_summary=run_metrics_module.token_summary(run_metrics),
            run_metrics_summary=run_metrics_module.run_summary(run_metrics),
            failure_summary=None,
            started_at=run_started_at,
            finished_at=_utc_now(),
            run_id=effective_run_id,
        )

    return final_state


def _record_run_artifacts(
    workspace_root: Path,
    workflow_name: str,
    workflow_version: str | None,
    input_state: dict[str, Any],
    final_state: dict[str, Any],
    status: str,
    workflow_source: str,
    dsl_summary: dict[str, Any],
    before_snapshot: run_changes_module.Snapshot | None,
    token_summary: dict[str, Any],
    run_metrics_summary: dict[str, Any],
    failure_summary: dict[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    run_id: str | None = None,
) -> None:
    after_snapshot = run_changes_module.capture_snapshot(workspace_root)
    record = run_records_module.build_run_record(
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        input_state=input_state,
        final_state=final_state,
        status=status,
        workflow_source=workflow_source,
        dsl_summary=dsl_summary,
        token_summary=token_summary,
        run_metrics_summary=run_metrics_summary,
        failure_summary=failure_summary,
        started_at=started_at,
        finished_at=finished_at,
        run_id=run_id,
    )
    manifest = run_changes_module.build_change_manifest(
        run_id=record["run_id"],
        status=status,
        workspace_root=workspace_root,
        before=before_snapshot or {"files": {}},
        after=after_snapshot,
    )
    record["change_summary"] = run_changes_module.change_summary(manifest)
    record["token_summary"] = token_summary
    record["run_metrics_summary"] = run_metrics_summary
    run_records_module.save_run_record(workspace_root, record)
    run_changes_module.save_change_artifacts(
        workspace_root,
        manifest,
        token_summary=token_summary,
        run_record=record,
        run_metrics_summary=run_metrics_summary,
        failure_summary=failure_summary,
    )


def _dsl_summary(dsl: dict[str, Any]) -> dict[str, Any]:
    nodes = dsl.get("nodes", [])
    edges = dsl.get("edges", [])
    routes = dsl.get("routes", [])
    return {
        "node_count": len(nodes) if isinstance(nodes, list) else None,
        "edge_count": len(edges) if isinstance(edges, list) else None,
        "route_count": len(routes) if isinstance(routes, list) else None,
        "entry_point": dsl.get("entry_point"),
    }


def _failure_summary(exc: Exception) -> dict[str, Any]:
    attached = getattr(exc, "__lgwf_failure__", None)
    failure = attached if isinstance(attached, dict) else progress_module.last_failure() or {}
    return {
        "node_id": failure.get("node_id"),
        "capability": failure.get("capability"),
        "error_type": failure.get("error_type") or type(exc).__name__,
        "message": failure.get("message") or str(exc),
    }


def _emit_workflow_failed(progress_writer: Callable[[str], None] | None, message: str, run_id: str | None = None) -> None:
    if progress_writer is not None:
        progress_writer(progress_module.with_run_id(message, run_id))
    else:
        progress_module.emit(message)


def _emit_workflow_timing(progress_writer: Callable[[str], None] | None, message: str, run_id: str | None = None) -> None:
    if progress_writer is not None:
        progress_writer(progress_module.with_run_id(message, run_id))


def _utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()



