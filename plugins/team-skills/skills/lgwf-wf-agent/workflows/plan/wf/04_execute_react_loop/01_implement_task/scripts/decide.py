from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MANUAL_APPROVAL_BLOCK = "manual_approval_required"


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def iter_values(value: Any) -> list[Any]:
    values = [value]
    if isinstance(value, dict):
        for item in value.values():
            values.extend(iter_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(iter_values(item))
    return values


def requires_manual_approval(result: dict) -> bool:
    if result.get("blocking_reason") == MANUAL_APPROVAL_BLOCK:
        return True

    for item in result.get("required_follow_up") or []:
        if not isinstance(item, dict):
            continue
        follow_type = str(item.get("type") or item.get("kind") or "").lower()
        if follow_type in {"approval", "manual_approval", MANUAL_APPROVAL_BLOCK}:
            return True
        if item.get("approval_artifact") or item.get("confirmed_artifact"):
            return True

    text_values = [str(item).lower() for item in iter_values(result) if isinstance(item, str)]
    manual_markers = (
        "manual_approval_required",
        "check_step_design_confirmation",
        "step_design_confirmation_record_absent",
        "step_designs_json_absent",
        "approval_artifact",
        "confirmed_artifact",
        "confirmation_record_absent",
    )
    return any(marker in text for marker in manual_markers for text in text_values)


def main() -> None:
    result = load(Path.cwd() / ".lgwf" / "react_task_result.json")
    passed = result.get("pass") is True or result.get("verdict") == "pass"
    next_step = "exit" if passed or requires_manual_approval(result) else "continue"
    print(json.dumps({"next": next_step}, ensure_ascii=False))


if __name__ == "__main__":
    main()

