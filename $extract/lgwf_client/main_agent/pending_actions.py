from typing import Any


def human_approval_action(request: dict[str, Any]) -> dict[str, Any]:
    request_id = request.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("human approval request_id must be a non-empty string.")
    return {
        "type": "human_approval",
        "request_id": request_id,
        "prompt": request.get("prompt"),
        "context": request.get("context"),
        "allowed_responses": ["approve", "reject"],
    }
