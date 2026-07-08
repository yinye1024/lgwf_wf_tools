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
    "target_paths",
    "allowed_dirs",
    "dsl_upgrade_target",
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


def _input_payload_from_command(command: Any) -> dict[str, Any]:
    if not isinstance(command, list):
        return {}
    for index, token in enumerate(command):
        if token == "--input-json" and index + 1 < len(command):
            value = command[index + 1]
            if isinstance(value, str) and value.strip():
                return json.loads(value)
        if token == "--input-json-file" and index + 1 < len(command):
            value = command[index + 1]
            if isinstance(value, str) and value.strip():
                input_path = Path(value)
                if input_path.is_file():
                    payload = json.loads(input_path.read_text(encoding="utf-8"))
                    return payload if isinstance(payload, dict) else {}
    return {}


def _load_session_input_payload(work_dir: Any) -> dict[str, Any]:
    if not isinstance(work_dir, str) or not work_dir:
        return {}
    sessions_dir = Path(work_dir) / ".lgwf" / "main_agent" / "sessions"
    if not sessions_dir.is_dir():
        return {}
    session_files = sorted(
        sessions_dir.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for session_file in session_files:
        session = read_json(session_file, {})
        payload = _input_payload_from_command(session.get("command"))
        if payload:
            return payload
    return {}


def _merge_session_input(payload: dict[str, Any]) -> dict[str, Any]:
    work_dir = payload.get("work_dir")
    if not isinstance(work_dir, str) or not work_dir:
        work_dir = str(Path.cwd())
    session_input = _load_session_input_payload(work_dir)
    if not session_input:
        if "work_dir" not in payload:
            merged_without_session = dict(payload)
            merged_without_session["work_dir"] = work_dir
            return merged_without_session
        return payload
    merged = dict(session_input)
    merged.update(payload)
    merged.setdefault("work_dir", work_dir)
    return merged


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
    payload = select_runtime_payload(load_stdin_json(), *expected_keys)
    return _merge_session_input(payload)


def _has_value(value: Any) -> bool:
    return value not in (None, "", [])


def find_payload_section(payload: Any, section_key: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    section = payload.get(section_key)
    if isinstance(section, dict):
        return section
    for key in WRAPPER_KEYS:
        nested = payload.get(key)
        found = find_payload_section(nested, section_key)
        if found:
            return found
    for nested in payload.values():
        if isinstance(nested, dict):
            found = find_payload_section(nested, section_key)
            if found:
                return found
    return {}


def get_dsl_upgrade_target(payload: Any) -> dict[str, Any]:
    section = find_payload_section(payload, "dsl_upgrade_target")
    if section:
        return section
    if isinstance(payload, dict) and any(key in payload for key in ("target_paths", "allowed_dirs")):
        return payload
    return {}


def get_runtime_field(payload: dict[str, Any], key: str, default: Any = None) -> Any:
    if _has_value(payload.get(key)):
        return payload[key]
    dsl_target = get_dsl_upgrade_target(payload)
    if key == "targets" and _has_value(dsl_target.get("target_paths")):
        return dsl_target["target_paths"]
    if _has_value(dsl_target.get(key)):
        return dsl_target[key]
    return default


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
