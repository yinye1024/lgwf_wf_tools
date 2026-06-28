import datetime
import os
import time
import uuid
from pathlib import Path
from typing import Any

import lgwf_tools.file_ops as file_ops_module
import lgwf_tools.workspace_layout as workspace_layout_module


HUMAN_APPROVAL_TOKEN_ENV = "LGWF_HUMAN_APPROVAL_TOKEN"
HUMAN_CONTROLLER_CALLER = "human_controller"
CONTROLLER_PAYLOAD_CREATORS = {"main_agent_ask"}


class HumanApprovalError(ValueError):
    """Raised when human approval files are invalid or unavailable."""


def create_request(
    workspace_root: Path,
    prompt: str,
    context: Any,
    request_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise HumanApprovalError("prompt must be a non-empty string.")
    request_id = request_id or f"human-{uuid.uuid4().hex[:12]}"
    request = {
        "request_id": request_id,
        "prompt": prompt,
        "context": context,
        "created_at": _utc_now(),
        "status": "pending",
    }
    path = _request_path(workspace_root, request_id)
    file_ops_module.write_json_atomic(path, request)
    return request


def list_pending_requests(workspace_root: Path) -> list[dict[str, Any]]:
    human_dir = workspace_layout_module.human_dir(workspace_root.resolve())
    if not human_dir.exists():
        return []
    requests: list[dict[str, Any]] = []
    paths = sorted(human_dir.glob("*.request.json"), key=_safe_mtime, reverse=True)
    for path in paths:
        if not path.is_file():
            continue
        request_id = path.name.removesuffix(".request.json")
        if _response_path(workspace_root, request_id).exists():
            continue
        requests.append(_load_json(path, "human request"))
    return requests


def load_request(workspace_root: Path, request_id: str) -> dict[str, Any]:
    path = _request_path(workspace_root, request_id)
    if not path.is_file():
        raise HumanApprovalError(f"human request not found: {request_id}")
    return _load_json(path, "human request")


def write_response(
    workspace_root: Path,
    request_id: str,
    response: dict[str, Any],
    *,
    caller: str = "agent",
    approval_token: str | None = None,
) -> Path:
    load_request(workspace_root, request_id)
    _validate_response_authority(caller, approval_token)
    _validate_response(response)
    response_payload = dict(response)
    response_payload["request_id"] = request_id
    response_payload["caller"] = caller
    response_payload["responded_at"] = _utc_now()
    path = _response_path(workspace_root, request_id)
    file_ops_module.write_json_atomic(path, response_payload)
    return path


def write_controller_payload(
    workspace_root: Path,
    request_id: str,
    payload: dict[str, Any],
) -> Path:
    load_request(workspace_root, request_id)
    _validate_controller_payload(payload, request_id)
    path = _controller_payload_path(workspace_root, request_id)
    file_ops_module.write_json_atomic(path, payload)
    return path


def load_controller_payload(workspace_root: Path, request_id: str) -> dict[str, Any]:
    load_request(workspace_root, request_id)
    path = _controller_payload_path(workspace_root, request_id)
    if not path.is_file():
        raise HumanApprovalError(f"controller payload not found: {request_id}")
    payload = _load_json(path, "human controller payload")
    _validate_controller_payload(payload, request_id)
    return payload


def submit_controller_payload(
    workspace_root: Path,
    request_id: str,
    final_user_confirmed: bool = True,
) -> Path:
    if final_user_confirmed is not True:
        raise HumanApprovalError("final user confirmation is required.")
    payload = load_controller_payload(workspace_root, request_id)
    response_payload: dict[str, Any] = {
        "request_id": request_id,
        "decision": payload["decision"],
        "caller": HUMAN_CONTROLLER_CALLER,
        "submitted_via": "controller_payload",
        "final_user_confirmed": True,
        "controller_payload": payload,
        "responded_at": _utc_now(),
    }
    if "value" in payload:
        response_payload["value"] = payload["value"]
    if "comment" in payload:
        response_payload["comment"] = payload["comment"]
    _validate_response(response_payload)
    path = _response_path(workspace_root, request_id)
    file_ops_module.write_json_atomic(path, response_payload)
    return path


def wait_for_response(
    workspace_root: Path,
    request_id: str,
    timeout_seconds: float | None,
    poll_interval_seconds: float,
) -> dict[str, Any]:
    deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
    path = _response_path(workspace_root, request_id)
    while deadline is None or time.monotonic() <= deadline:
        if path.is_file():
            try:
                response = _load_json(path, "human response")
            except PermissionError:
                time.sleep(poll_interval_seconds)
                continue
            _validate_response(response)
            return response
        time.sleep(poll_interval_seconds)
    raise TimeoutError(f"Human approval timed out: {request_id}")


def _validate_response(response: dict[str, Any]) -> None:
    if not isinstance(response, dict):
        raise HumanApprovalError("human response must be a JSON object.")
    decision = response.get("decision")
    if decision not in {"approve", "reject"}:
        raise HumanApprovalError("human response decision must be approve or reject.")
    if decision == "approve" and "value" not in response:
        raise HumanApprovalError("approve response must include value.")
    comment = response.get("comment", "")
    if comment is not None and not isinstance(comment, str):
        raise HumanApprovalError("human response comment must be a string when provided.")


def _validate_controller_payload(payload: dict[str, Any], request_id: str) -> None:
    if not isinstance(payload, dict):
        raise HumanApprovalError("controller payload must be a JSON object.")
    if payload.get("request_id") != request_id:
        raise HumanApprovalError("controller payload request_id mismatch.")
    decision = payload.get("decision")
    if decision not in {"approve", "reject"}:
        raise HumanApprovalError("controller payload decision must be approve or reject.")
    if decision == "approve" and "value" not in payload:
        raise HumanApprovalError("approve payload must include value.")
    if decision == "reject" and "value" not in payload and "comment" not in payload:
        raise HumanApprovalError("reject payload must include comment or value.")
    if payload.get("created_by") not in CONTROLLER_PAYLOAD_CREATORS:
        allowed = ", ".join(sorted(CONTROLLER_PAYLOAD_CREATORS))
        raise HumanApprovalError(f"controller payload created_by must be one of: {allowed}.")
    created_at = payload.get("created_at")
    if not isinstance(created_at, str) or not created_at:
        raise HumanApprovalError("controller payload created_at must be a non-empty string.")
    comment = payload.get("comment", "")
    if comment is not None and not isinstance(comment, str):
        raise HumanApprovalError("controller payload comment must be a string when provided.")


def _validate_response_authority(caller: str, approval_token: str | None) -> None:
    if caller != HUMAN_CONTROLLER_CALLER:
        raise HumanApprovalError("human approval response requires caller=human_controller.")
    expected_token = os.environ.get(HUMAN_APPROVAL_TOKEN_ENV)
    if not expected_token or approval_token != expected_token:
        raise HumanApprovalError("invalid human approval token.")


def _request_path(workspace_root: Path, request_id: str) -> Path:
    _validate_request_id(request_id)
    return workspace_layout_module.human_request_path(workspace_root.resolve(), request_id)


def _response_path(workspace_root: Path, request_id: str) -> Path:
    _validate_request_id(request_id)
    return workspace_layout_module.human_response_path(workspace_root.resolve(), request_id)


def _controller_payload_path(workspace_root: Path, request_id: str) -> Path:
    _validate_request_id(request_id)
    return workspace_layout_module.human_controller_payload_path(workspace_root.resolve(), request_id)


def _validate_request_id(request_id: str) -> None:
    if not isinstance(request_id, str) or not request_id:
        raise HumanApprovalError("request_id must be a non-empty string.")
    if "/" in request_id or "\\" in request_id or ".." in request_id:
        raise HumanApprovalError("request_id must not contain path separators or '..'.")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        data = file_ops_module.read_json(path)
    except file_ops_module.FileOperationError as exc:
        raise HumanApprovalError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(data, dict):
        raise HumanApprovalError(f"{label} must be a JSON object: {path}")
    return data


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _utc_now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()

