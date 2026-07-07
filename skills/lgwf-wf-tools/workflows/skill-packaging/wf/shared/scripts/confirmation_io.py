from __future__ import annotations

import json
import sys
from typing import Any


def load_input() -> Any:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {"value": data}


def ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {"value": value}


def emit_json(value: Any) -> None:
    json.dump(value, sys.stdout, ensure_ascii=False, indent=2)


def wrap_confirmation(stage: str, proposal: Any) -> dict[str, Any]:
    return {
        "stage": stage,
        "proposal": ensure_dict(proposal),
        "decision_options": ["approve", "reject"],
        "notes": "当前初稿先使用二元审批；修订闭环可在后续迭代补强。",
    }
