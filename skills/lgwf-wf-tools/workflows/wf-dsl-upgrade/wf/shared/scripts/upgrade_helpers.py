from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


WRAPPER_KEYS = (
    "input",
    "inputs",
    "payload",
    "value",
    "context",
    "request",
    "data",
    "workflow_input",
    "state_input",
)

SIGNAL_KEYS = {
    "work_dir",
    "mode",
    "scope_mode",
    "targets",
    "max_targets",
    "decision",
    "approval",
    "route",
}


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_stdin_json() -> Any:
    import json
    import sys

    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def _iter_payload_candidates(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    candidates: list[dict[str, Any]] = [payload]
    for key in WRAPPER_KEYS:
        value = payload.get(key)
        if isinstance(value, dict):
            candidates.extend(_iter_payload_candidates(value))
    for value in payload.values():
        if isinstance(value, dict) and SIGNAL_KEYS.intersection(value):
            candidates.extend(_iter_payload_candidates(value))
    return candidates


def select_runtime_payload(payload: Any, *expected_keys: str) -> dict[str, Any]:
    candidates = _iter_payload_candidates(payload)
    if not candidates:
        return {}
    if not expected_keys:
        return candidates[0]
    best = max(
        candidates,
        key=lambda item: sum(1 for key in expected_keys if key in item and item.get(key) not in (None, "", [])),
    )
    if any(key in best and best.get(key) not in (None, "", []) for key in expected_keys):
        return best
    return candidates[0]


def load_runtime_payload(*expected_keys: str) -> dict[str, Any]:
    return select_runtime_payload(load_stdin_json(), *expected_keys)


def normalize_decision_value(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("decision", "approval", "route", "value"):
            normalized = normalize_decision_value(value.get(key))
            if normalized:
                return normalized
        return ""
    if value in (None, ""):
        return ""
    return str(value).strip().lower()


def extract_decision(payload: Any, default: str = "reject") -> str:
    for candidate in _iter_payload_candidates(payload):
        for key in ("decision", "approval", "route", "value"):
            decision = normalize_decision_value(candidate.get(key))
            if decision:
                return decision
    return default


def dump_state_updates(payload: dict[str, Any]) -> None:
    import json
    import sys

    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
