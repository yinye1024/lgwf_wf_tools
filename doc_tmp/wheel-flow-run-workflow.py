from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import lgwf.capabilities.flow.flow_conditions as flow_conditions_module
import lgwf.capabilities.types as capability_types
import lgwf.checkpoints as checkpoints_module
import lgwf.progress as progress_module
import lgwf.resume as resume_module
import lgwf.runtime_context as runtime_context_module
import lgwf.runs.records as run_records_module
import lgwf.file_ops as file_ops_module
import lgwf.light_isolation as light_isolation_module
import lgwf.workspace_layout as workspace_layout_module
import lgwf_client.workflow_package.package_snapshot as package_snapshot_module


POLL_INTERVAL_SECONDS = 0.5


class FlowRunWorkflowCapability:
    name = "flow.run_workflow"

    def create_node(self, node_id: str, config: dict[str, Any]) -> capability_types.NodeCallable:
        workflow_lgwf = config.get("workflow_lgwf")
        work_dir = config.get("work_dir")
        input_path = config.get("input_path")
        result_path = config.get("result_path")
        if not isinstance(workflow_lgwf, str) or not workflow_lgwf:
            raise ValueError("flow.run_workflow config.workflow_lgwf must be a non-empty string.")
        if not isinstance(work_dir, str) or not work_dir:
            raise ValueError("flow.run_workflow config.work_dir must be a non-empty string.")
        if not isinstance(input_path, str) or not input_path:
            raise ValueError("flow.run_workflow config.input_path must be a non-empty string.")
        if not isinstance(result_path, str) or not result_path:
            raise ValueError("flow.run_workflow config.result_path must be a non-empty string.")

        def node(state: capability_types.State) -> capability_types.State:
            parent_root = runtime_context_module.get_workspace_root()
            if parent_root is None:
                raise RuntimeError("flow.run_workflow requires a parent runtime workspace root.")
            child_input = flow_conditions_module.read_path(state, input_path)
            if not isinstance(child_input, dict):
                raise ValueError("flow.run_workflow INPUT must resolve to a JSON object.")

            declared_child_work_dir = _resolve_repo_relative(work_dir)
            resume_this_node = resume_module.get_resume_target() == node_id
            if resume_this_node:
                isolation = light_isolation_module.existing_isolation(
                    parent_work_dir=parent_root,
                    namespace="run_workflow",
                    key=node_id,
                )
                if not isolation.work_dir.exists() or not isolation.workspace.exists():
                    isolation = light_isolation_module.prepare_isolation(
                        parent_work_dir=parent_root,
                        source_workspace=Path.cwd(),
                        namespace="run_workflow",
                        key=node_id,
                    )
                    resume_this_node = False
            else:
                isolation = light_isolation_module.prepare_isolation(
                    parent_work_dir=parent_root,
                    source_workspace=Path.cwd(),
                    namespace="run_workflow",
                    key=node_id,
                )
            child_workspace = isolation.workspace
            child_work_dir = isolation.work_dir
            child_workflow_lgwf = _resolve_relative_to(child_workspace, workflow_lgwf)
            child_record_path = workspace_layout_module.child_run_path(parent_root, node_id)
            child_artifact_dir = workspace_layout_module.child_runs_dir(parent_root) / node_id
            child_artifact_dir.mkdir(parents=True, exist_ok=True)
            input_json_path = child_artifact_dir / "input.json"
            stdout_path = child_artifact_dir / "stdout.log"
            stderr_path = child_artifact_dir / "stderr.log"
            file_ops_module.write_json_atomic(input_json_path, child_input, sort_keys=True)

            base_record = {
                "node_id": node_id,
                "status": "preparing",
                "workflow_lgwf": str(child_workflow_lgwf),
                "declared_work_dir": str(declared_child_work_dir),
                "workspace": str(child_workspace),
                "work_dir": str(child_work_dir),
                "input_json": str(input_json_path),
                "stdout": str(stdout_path),
                "stderr": str(stderr_path),
            }
            _write_child_record(child_record_path, base_record)
            progress_module.emit(
                f"[workflow] child workflow preparing id={node_id} workflow_lgwf={child_workflow_lgwf} work_dir={child_work_dir}"
            )
            try:
                with _temporary_cwd(child_workspace):
                    snapshot = _existing_snapshot(child_work_dir) if resume_this_node else None
                    if snapshot is None:
                        snapshot = package_snapshot_module.copy_workflow_package(child_workflow_lgwf, child_work_dir)
                    snapshot_lgwf = Path(snapshot["workflow_lgwf"])
                    snapshot_json = Path(snapshot["workflow_json"])
                    if not resume_this_node:
                        import lgwf_dsl.auditor as dsl_auditor_module
                        import lgwf_dsl.compiler as dsl_compiler_module

                        audit_payload, audit_exit_code = dsl_auditor_module.WorkflowAuditor().audit(snapshot_lgwf)
                        if audit_exit_code != 0:
                            raise RuntimeError(f"child workflow audit failed: {audit_payload.get('summary')}")
                        workflow = dsl_compiler_module.WorkflowDslCompiler().compile_text(
                            snapshot_lgwf.read_text(encoding="utf-8"),
                            source_name=str(snapshot_lgwf),
                            package_root=snapshot_lgwf.parent,
                        )
                        file_ops_module.write_json_atomic(snapshot_json, workflow, sort_keys=True)
                    process = _start_child_process(
                        workflow_json=snapshot_json,
                        work_dir=child_work_dir,
                        child_input=child_input,
                        stdout_path=stdout_path,
                        stderr_path=stderr_path,
                        cwd=child_workspace,
                        resume_args=_child_resume_args(child_work_dir) if resume_this_node else [],
                    )
                running_record = {
                    **base_record,
                    "status": "running",
                    "pid": process.pid,
                    "snapshot": snapshot,
                }
                _write_child_record(child_record_path, running_record)
                progress_module.emit(
                    f"[workflow] child workflow started id={node_id} pid={process.pid} workflow_json={snapshot_json}"
                )
                returncode = _wait_for_child(process, child_record_path, running_record, child_work_dir)
                stdout_text = _read_text_if_exists(stdout_path)
                stderr_text = _read_text_if_exists(stderr_path)
                final_state = _parse_final_state(stdout_text)
                if returncode != 0:
                    result = _child_result(
                        node_id=node_id,
                        status="failed",
                        workflow_lgwf=child_workflow_lgwf,
                        declared_work_dir=declared_child_work_dir,
                        workspace=child_workspace,
                        work_dir=child_work_dir,
                        final_state=final_state,
                        failure={
                            "error_type": "ChildWorkflowFailed",
                            "message": f"child workflow exited with returncode {returncode}",
                            "returncode": returncode,
                            "stderr_tail": _tail(stderr_text),
                        },
                    )
                    _write_child_record(child_record_path, {**running_record, **result, "returncode": returncode})
                    raise RuntimeError(f"child workflow failed: {node_id} returncode={returncode}")

                result = _child_result(
                    node_id=node_id,
                    status="completed",
                    workflow_lgwf=child_workflow_lgwf,
                    declared_work_dir=declared_child_work_dir,
                    workspace=child_workspace,
                    work_dir=child_work_dir,
                    final_state=final_state,
                    failure=None,
                )
                _write_child_record(child_record_path, {**running_record, **result, "returncode": returncode})
                return flow_conditions_module.write_path(dict(state), result_path, result)
            except Exception as exc:
                latest = _latest_run(child_work_dir)
                existing_record = _read_child_record(child_record_path)
                failure = {
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
                if latest and latest.get("failure"):
                    failure["latest_run_failure"] = latest["failure"]
                _write_child_record(
                    child_record_path,
                    {
                        **base_record,
                        **existing_record,
                        "status": "failed",
                        "latest_run": latest,
                        "failure": failure,
                    },
                )
                raise

        return node


CAPABILITY = FlowRunWorkflowCapability()


def _start_child_process(
    *,
    workflow_json: Path,
    work_dir: Path,
    child_input: dict[str, Any],
    stdout_path: Path,
    stderr_path: Path,
    cwd: Path,
    resume_args: list[str] | None = None,
) -> subprocess.Popen:
    input_json_path = work_dir / ".lgwf" / "child-input.json"
    file_ops_module.ensure_dir(input_json_path.parent)
    file_ops_module.write_json_atomic(input_json_path, child_input, sort_keys=True)
    command = [
        sys.executable,
        "-m",
        "lgwf_client.cli",
        "--workflow-json",
        str(workflow_json),
        "--work-dir",
        str(work_dir),
        "--input-json-file",
        str(input_json_path),
    ]
    if resume_args:
        command.extend(resume_args)
    stdout_handle = stdout_path.open("w", encoding="utf-8")
    stderr_handle = stderr_path.open("w", encoding="utf-8")
    try:
        process = subprocess.Popen(
            command,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
            cwd=cwd,
        )
        stdout_handle.close()
        stderr_handle.close()
        return process
    except Exception:
        stdout_handle.close()
        stderr_handle.close()
        raise


def _existing_snapshot(child_work_dir: Path) -> dict[str, str] | None:
    workflow_dir = workspace_layout_module.lgwf_dir(child_work_dir) / "workflow"
    snapshot_lgwf = workflow_dir / "workflow.lgwf"
    snapshot_json = workflow_dir / "workflow.json"
    if not snapshot_lgwf.is_file() or not snapshot_json.is_file():
        return None
    return {
        "workflow_lgwf": str(snapshot_lgwf),
        "workflow_json": str(snapshot_json),
        "workflow_dir": str(workflow_dir),
    }


def _child_resume_args(child_work_dir: Path) -> list[str]:
    candidates: list[dict[str, Any]] = []
    for status in ({"failed"}, {"stopped"}, {"running"}):
        checkpoint = checkpoints_module.latest_checkpoint_with_status(child_work_dir, status)
        if checkpoint is not None:
            candidates.append(checkpoint)
    if not candidates:
        return []
    checkpoint = max(candidates, key=lambda item: str(item.get("updated_at", "")))
    run_id = checkpoint.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        return []
    args = ["--resume-run-id", run_id]
    if checkpoint.get("status") == "running":
        args.append("--resume-orphaned-running")
    else:
        args.append("--resume-allow-workflow-changed")
    return args


def _wait_for_child(
    process: subprocess.Popen,
    child_record_path: Path,
    running_record: dict[str, Any],
    child_work_dir: Path,
) -> int:
    while True:
        returncode = process.poll()
        latest_run = _latest_run(child_work_dir)
        _write_child_record(
            child_record_path,
            {
                **running_record,
                "status": "running" if returncode is None else "exited",
                "returncode": returncode,
                "latest_run": latest_run,
                "updated_at_unix": time.time(),
            },
        )
        if returncode is not None:
            return int(returncode)
        time.sleep(POLL_INTERVAL_SECONDS)


def _resolve_repo_relative(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("flow.run_workflow paths must be relative and must not contain '..'.")
    return path.resolve()


def _resolve_relative_to(root: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("flow.run_workflow paths must be relative and must not contain '..'.")
    return (root / path).resolve()


@contextmanager
def _temporary_cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _child_result(
    *,
    node_id: str,
    status: str,
    workflow_lgwf: Path,
    declared_work_dir: Path,
    workspace: Path,
    work_dir: Path,
    final_state: dict[str, Any] | None,
    failure: dict[str, Any] | None,
) -> dict[str, Any]:
    latest_run = _latest_run(work_dir)
    result: dict[str, Any] = {
        "node_id": node_id,
        "status": status,
        "workflow_lgwf": str(workflow_lgwf),
        "declared_work_dir": str(declared_work_dir),
        "workspace": str(workspace),
        "work_dir": str(work_dir),
        "latest_run": latest_run,
    }
    if final_state is not None:
        result["final_state"] = final_state
    if latest_run is not None:
        result["run_id"] = latest_run.get("run_id")
        result["token_usage"] = latest_run.get("token_usage", {})
        if latest_run.get("failure"):
            result["latest_run_failure"] = latest_run["failure"]
    if failure is not None:
        result["failure"] = failure
    return result


def _latest_run(work_dir: Path) -> dict[str, Any] | None:
    runs_dir = workspace_layout_module.runs_dir(work_dir)
    if not runs_dir.is_dir():
        return None
    paths = [path for path in runs_dir.glob("*/record.json")]
    if not paths:
        return None
    latest = max(paths, key=lambda path: path.stat().st_mtime)
    try:
        record = run_records_module.load_run_record(latest)
        trace_path = workspace_layout_module.run_trace_path(work_dir, record["run_id"])
        if trace_path.is_file():
            trace = file_ops_module.read_json(trace_path)
            if isinstance(trace, dict):
                record["token_usage"] = trace.get("token_usage", {})
        return record
    except Exception:
        return None


def _parse_final_state(stdout_text: str) -> dict[str, Any] | None:
    for line in reversed(stdout_text.splitlines()):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        return value if isinstance(value, dict) else None
    return None


def _read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _tail(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def _write_child_record(path: Path, data: dict[str, Any]) -> None:
    file_ops_module.write_json_atomic(path, data, sort_keys=True)


def _read_child_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = file_ops_module.read_json(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}
