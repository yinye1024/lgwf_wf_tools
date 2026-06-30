from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def find_raw_intent(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if not isinstance(payload, dict):
        return ""
    for key in ("raw_intent", "request", "workflow_request", "intent", "prompt"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    state = payload.get("state")
    if isinstance(state, dict):
        return find_raw_intent(state)
    return ""


def read_latest_checkpoint_state(lgwf_dir: Path) -> dict[str, Any]:
    checkpoints_dir = lgwf_dir / "checkpoints"
    if not checkpoints_dir.exists():
        return {}

    candidates = sorted(
        checkpoints_dir.glob("*/checkpoint.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates:
        checkpoint = read_json(path)
        for key in ("state_before_current_node", "state_after_current_node", "state"):
            state = checkpoint.get(key)
            if isinstance(state, dict) and find_raw_intent(state):
                return state
        if find_raw_intent(checkpoint):
            return checkpoint
    return {}


def main() -> None:
    cwd = Path.cwd()
    lgwf_dir = cwd / ".lgwf"
    lgwf_dir.mkdir(parents=True, exist_ok=True)

    candidates = [
        lgwf_dir / "input.json",
        lgwf_dir / "context.json",
        lgwf_dir / "run_input.json",
    ]
    context: dict[str, Any] = {}
    for path in candidates:
        context.update(read_json(path))

    env_input = os.environ.get("LGWF_INPUT_JSON")
    if env_input:
        try:
            context.update(json.loads(env_input))
        except json.JSONDecodeError:
            context["raw_intent"] = env_input

    raw_intent = find_raw_intent(context)
    if not raw_intent:
        raw_intent = find_raw_intent(read_latest_checkpoint_state(lgwf_dir))

    request = {
        "raw_intent": raw_intent,
        "need_user_clarification": not bool(raw_intent),
        "source": "lgwf-wf-thinking",
        "notes": [] if raw_intent else ["未发现 raw_intent；后续 confirm_plan 需要用户补充需求。"],
    }
    (lgwf_dir / "lgwf_wf_thinking_request.json").write_text(
        json.dumps(request, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"lgwf_wf_thinking.request": request}, ensure_ascii=False))


if __name__ == "__main__":
    main()
