from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dsl_upgrade_common import load_json, run_lgwf_audit, write_json


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def _audit_from_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    audit_file = load_json(root / ".lgwf" / "current_target_audit.json", {})
    if isinstance(audit_file, dict) and audit_file:
        return audit_file
    nested_audit = payload.get("audit")
    if isinstance(nested_audit, dict):
        return nested_audit
    if payload.get("path"):
        target_path = Path(str(payload["path"])).expanduser().resolve()
        audit = run_lgwf_audit(target_path)
        audit["status"] = "completed"
        write_json(root / ".lgwf" / "current_target_audit.json", audit)
        return audit
    return payload


def _observation_from_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if any(key in payload for key in ("post_hash", "diagnostic_delta", "diagnostic_identities")):
        return payload
    observation = load_json(root / ".lgwf" / "repair_observation.json", {})
    return observation if isinstance(observation, dict) else {}


def _same_diagnostics(observation: dict[str, Any]) -> bool:
    current = observation.get("diagnostic_identities", [])
    previous = observation.get("previous_diagnostic_identities", [])
    if isinstance(current, list) and isinstance(previous, list) and previous:
        return current == previous
    return int(observation.get("diagnostic_delta", 0) or 0) == 0


def decide_next(audit: dict[str, Any], observation: dict[str, Any] | None = None) -> dict[str, Any]:
    passed = bool(audit.get("passed"))
    diagnostics = audit.get("diagnostics", [])
    diagnostic_count = len(diagnostics) if isinstance(diagnostics, list) else 0
    if passed:
        return {
            "next": "exit",
            "repair_decision": {
                "status": "passed",
                "reason": "audit 已通过，结束当前目标修复。",
                "diagnostic_count": diagnostic_count,
            },
        }
    observation = observation or {}
    has_observation = any(key in observation for key in ("changed", "diagnostic_delta", "diagnostic_identities"))
    diagnostic_delta = int(observation.get("diagnostic_delta", 0) or 0)
    changed = bool(observation.get("changed"))
    status = "retry"
    reason = "audit check 仍有 diagnostics，继续下一轮 reason 必须逐条给出修正方案。"
    if has_observation and not changed and _same_diagnostics(observation):
        status = "no_progress"
        reason = "audit check 仍失败，且本轮目标文件与 diagnostics 未变化；下一轮 reason 必须直接针对剩余 diagnostics 给出修正方案。"
    elif has_observation and diagnostic_delta < 0:
        status = "improved_retry"
        reason = "audit check 仍失败，但 diagnostics 数量下降；继续修复剩余 diagnostics。"
    return {
        "next": "continue",
        "repair_decision": {
            "status": status,
            "reason": reason,
            "diagnostic_count": diagnostic_count,
            "diagnostic_delta": diagnostic_delta,
            "changed": changed,
            "diagnostic_identities": observation.get("diagnostic_identities", []),
        },
    }


def main() -> None:
    root = Path.cwd()
    payload = _read_payload()
    audit = _audit_from_payload(root, payload)
    observation = _observation_from_payload(root, payload)
    write_json(root / ".lgwf" / "current_target_audit.json", audit)
    decision = decide_next(audit, observation)
    print(
        json.dumps(
            {
                "next": decision["next"],
                "wf_dsl_upgrade.current_audit": audit,
                "wf_dsl_upgrade.repair_decision": decision["repair_decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
