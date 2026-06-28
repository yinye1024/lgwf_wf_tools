import datetime
import uuid
from pathlib import Path
from typing import Any

import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module

MAX_STRING_LENGTH = 500
MAX_LIST_ITEMS = 20
MAX_DICT_ITEMS = 50


RunRecord = dict[str, Any]


class RunRecordError(ValueError):
    """Raised when workflow run records cannot be saved or loaded."""


def build_run_record(
    workflow_name: str,
    workflow_version: str | None,
    input_state: dict[str, Any],
    final_state: dict[str, Any],
    status: str = "completed",
    workflow_source: str = "registry",
    dsl_summary: dict[str, Any] | None = None,
    change_summary: dict[str, Any] | None = None,
    token_summary: dict[str, Any] | None = None,
    run_metrics_summary: dict[str, Any] | None = None,
    failure_summary: dict[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    run_id: str | None = None,
) -> RunRecord:
    if not workflow_name:
        raise RunRecordError("workflow_name must be non-empty.")
    if workflow_version is not None and not workflow_version:
        raise RunRecordError("workflow_version must be non-empty when provided.")
    if status not in {"completed", "failed"}:
        raise RunRecordError("status must be completed or failed.")
    if workflow_source not in {"registry", "dynamic"}:
        raise RunRecordError("workflow_source must be registry or dynamic.")

    now = _utc_now()
    effective_run_id = run_id or new_run_id(now)
    if not isinstance(effective_run_id, str) or not effective_run_id:
        raise RunRecordError("run_id must be a non-empty string when provided.")
    start_time = started_at or now
    finish_time = finished_at or now

    record = {
        "version": 1,
        "run_id": effective_run_id,
        "workflow": {
            "source": workflow_source,
            "name": workflow_name,
            "version": workflow_version,
        },
        "status": status,
        "started_at": start_time,
        "finished_at": finish_time,
        "dsl_summary": _summarize(dsl_summary or {}),
        "input_summary": _summarize(input_state),
        "final_state_summary": _summarize(final_state),
        "change_summary": _summarize(change_summary or {}),
        "token_summary": _summarize(token_summary or {}),
        "run_metrics_summary": _summarize(run_metrics_summary or {}),
    }
    if failure_summary is not None:
        record["failure_summary"] = _summarize(failure_summary)
    return record


def save_run_record(workspace_root: Path, record: RunRecord) -> Path:
    _validate_record(record)
    runs_dir = workspace_layout_module.runs_dir(workspace_root.resolve())
    file_ops_module.ensure_dir(runs_dir)
    path = workspace_layout_module.run_record_path(workspace_root.resolve(), record["run_id"])
    file_ops_module.write_json_atomic(path, record)
    return path


def load_run_record(path: Path) -> RunRecord:
    try:
        data = file_ops_module.read_json(path)
    except FileNotFoundError as exc:
        raise RunRecordError(f"Workflow run record not found: {path}") from exc
    except OSError as exc:
        raise RunRecordError(f"Failed to read workflow run record: {path}") from exc
    except file_ops_module.FileOperationError as exc:
        raise RunRecordError(f"Workflow run record is not valid JSON: {path}") from exc

    _validate_record(data)
    return data


def record_run(
    workspace_root: Path,
    workflow_name: str,
    workflow_version: str | None,
    input_state: dict[str, Any],
    final_state: dict[str, Any],
    status: str = "completed",
    workflow_source: str = "registry",
    dsl_summary: dict[str, Any] | None = None,
    change_summary: dict[str, Any] | None = None,
    token_summary: dict[str, Any] | None = None,
    run_metrics_summary: dict[str, Any] | None = None,
    failure_summary: dict[str, Any] | None = None,
) -> Path:
    record = build_run_record(
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        input_state=input_state,
        final_state=final_state,
        status=status,
        workflow_source=workflow_source,
        dsl_summary=dsl_summary,
        change_summary=change_summary,
        token_summary=token_summary,
        run_metrics_summary=run_metrics_summary,
        failure_summary=failure_summary,
    )
    return save_run_record(workspace_root, record)


def new_run_id(timestamp: str | None = None) -> str:
    now = timestamp or _utc_now()
    return f"{now.replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:8]}"


def _summarize(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for index, key in enumerate(sorted(value, key=str)):
            if index >= MAX_DICT_ITEMS:
                result["__truncated__"] = True
                break
            result[str(key)] = _summarize(value[key])
        return result

    if isinstance(value, list):
        result = [_summarize(item) for item in value[:MAX_LIST_ITEMS]]
        if len(value) > MAX_LIST_ITEMS:
            result.append({"__truncated__": True})
        return result

    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            return value[:MAX_STRING_LENGTH] + "...[truncated]"
        return value

    if isinstance(value, int | float | bool) or value is None:
        return value

    return repr(value)


def _validate_record(data: Any) -> None:
    if not isinstance(data, dict):
        raise RunRecordError("Workflow run record root must be an object.")
    if data.get("version") != 1:
        raise RunRecordError("Workflow run record version must be 1.")

    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise RunRecordError("Workflow run record run_id must be a non-empty string.")

    workflow = data.get("workflow")
    if not isinstance(workflow, dict):
        raise RunRecordError("Workflow run record workflow must be an object.")
    source = workflow.get("source")
    if source not in {"registry", "dynamic"}:
        raise RunRecordError("Workflow run record workflow.source must be registry or dynamic.")
    name = workflow.get("name")
    if not isinstance(name, str) or not name:
        raise RunRecordError("Workflow run record workflow.name must be a non-empty string.")
    version = workflow.get("version")
    if version is not None and (not isinstance(version, str) or not version):
        raise RunRecordError("Workflow run record workflow.version must be a non-empty string when provided.")

    if data.get("status") not in {"completed", "failed"}:
        raise RunRecordError("Workflow run record status must be completed or failed.")

    for field in ("started_at", "finished_at"):
        value = data.get(field)
        if not isinstance(value, str) or not value:
            raise RunRecordError(f"Workflow run record {field} must be a non-empty string.")

    if "input_summary" not in data:
        raise RunRecordError("Workflow run record must include input_summary.")
    if "final_state_summary" not in data:
        raise RunRecordError("Workflow run record must include final_state_summary.")
    if "dsl_summary" not in data:
        raise RunRecordError("Workflow run record must include dsl_summary.")
    failure_summary = data.get("failure_summary")
    if failure_summary is not None and not isinstance(failure_summary, dict):
        raise RunRecordError("Workflow run record failure_summary must be an object when provided.")


def _utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


