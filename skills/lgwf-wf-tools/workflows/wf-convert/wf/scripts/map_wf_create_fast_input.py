from __future__ import annotations

import json
import sys
from typing import Any


def validate_wf_create_fast_input(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("wf-create-fast 创建输入必须是 JSON object")
    raw_intent = value.get("raw_intent")
    if not isinstance(raw_intent, str) or not raw_intent.strip():
        raise ValueError("wf-create-fast 创建输入缺少非空 raw_intent")
    return value


def extract_wf_create_fast_input(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("wf_create_fast_payload 必须是 JSON object")

    candidates: list[dict[str, Any]] = []
    namespaced_payload = payload.get("lgwf_wf_convert.wf_create_fast_payload")
    if isinstance(namespaced_payload, dict):
        candidates.append(namespaced_payload)
    namespaced_input = payload.get("lgwf_wf_convert.wf_create_fast_input")
    if isinstance(namespaced_input, dict):
        candidates.append(namespaced_input)
    candidates.append(payload)

    for candidate in candidates:
        nested_fast_payload = candidate.get("wf_create_fast_payload")
        if isinstance(nested_fast_payload, dict):
            return validate_wf_create_fast_input(nested_fast_payload)
        nested_input = candidate.get("wf_create_fast_input")
        if isinstance(nested_input, dict):
            return validate_wf_create_fast_input(nested_input)
        if "raw_intent" in candidate:
            return validate_wf_create_fast_input(candidate)

    raise ValueError("wf_create_fast_payload 缺少 wf-create-fast 创建输入")


def main() -> None:
    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    child_input = extract_wf_create_fast_input(payload)
    print(json.dumps({"lgwf_wf_convert.wf_create_fast_input": child_input}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
