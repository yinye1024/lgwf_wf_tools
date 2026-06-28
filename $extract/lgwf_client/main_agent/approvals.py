import datetime
import pathlib
from typing import Any

import lgwf.human_approval as human_approval_module


MISSING = object()


def submit_main_agent_approval(
    work_dir: str | pathlib.Path,
    request_id: str,
    *,
    decision: str,
    value: Any = MISSING,
    comment: str | None = None,
) -> dict[str, Any]:
    root = pathlib.Path(work_dir).expanduser().resolve()
    payload = _controller_payload(
        request_id=request_id,
        decision=decision,
        value=value,
        comment=comment,
    )
    human_approval_module.write_controller_payload(root, request_id, payload)
    response_path = human_approval_module.submit_controller_payload(root, request_id, final_user_confirmed=True)
    return {
        "ok": True,
        "request_id": request_id,
        "response_path": str(response_path),
    }


def _controller_payload(
    *,
    request_id: str,
    decision: str,
    value: Any,
    comment: str | None,
) -> dict[str, Any]:
    if decision not in {"approve", "reject"}:
        raise ValueError("decision must be approve or reject.")
    if decision == "approve" and value is MISSING:
        raise ValueError("approve requires value-json.")
    if decision == "reject" and (comment is None or not comment.strip()):
        raise ValueError("reject requires comment.")

    payload: dict[str, Any] = {
        "request_id": request_id,
        "decision": decision,
        "created_by": "main_agent_ask",
        "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    if value is not MISSING:
        payload["value"] = value
    if comment is not None:
        payload["comment"] = comment
    return payload
