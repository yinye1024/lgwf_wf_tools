from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from dsl_upgrade_common import run_lgwf_audit, write_json


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def _audit_from_payload(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("path"):
        target_path = Path(str(payload["path"])).expanduser().resolve()
        audit = run_lgwf_audit(target_path)
        audit["status"] = "completed"
        write_json(root / ".lgwf" / "current_target_audit.json", audit)
        return audit
    return payload


def decide_next(audit: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "next": "continue",
        "repair_decision": {
            "status": "retry",
            "reason": "audit 仍有 diagnostics，继续下一轮最小修复。",
            "diagnostic_count": diagnostic_count,
        },
    }


def main() -> None:
    audit = _audit_from_payload(Path.cwd(), _read_payload())
    decision = decide_next(audit)
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
