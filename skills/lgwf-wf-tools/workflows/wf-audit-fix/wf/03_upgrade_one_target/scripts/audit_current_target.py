from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dsl_upgrade_common import diagnostic_identity, load_json, run_lgwf_audit, write_json


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def _diagnostics(audit: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics = audit.get("diagnostics", [])
    return diagnostics if isinstance(diagnostics, list) else []


def _diagnostic_identities(audit: dict[str, Any]) -> list[str]:
    return [diagnostic_identity(item) for item in _diagnostics(audit) if isinstance(item, dict)]


def _repair_context(root: Path, target: dict[str, Any]) -> dict[str, Any]:
    context = load_json(root / ".lgwf" / "current_target_context.json", {})
    return context if isinstance(context, dict) else {}


def initial_repair_feedback(root: Path, target: dict[str, Any], audit: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _repair_context(root, target)
    merged = {**context, **target}
    diagnostics = _diagnostics(audit)
    identities = _diagnostic_identities(audit)
    diagnostic_count = len(diagnostics)
    mode = str(merged.get("mode", "dry_run"))
    observation = {
        "phase": "initial_audit",
        "authorized": bool(merged.get("authorized", False)),
        "target_path": str(Path(str(merged.get("path", ""))).expanduser().resolve()),
        "mode": mode,
        "pre_hash": str(merged.get("pre_hash", "") or ""),
        "current_hash": str(merged.get("current_hash", "") or ""),
        "post_hash": str(merged.get("current_hash", "") or ""),
        "changed": False,
        "passed": bool(audit.get("passed")),
        "diagnostic_count": diagnostic_count,
        "diagnostics": diagnostics,
        "diagnostic_identities": identities,
        "previous_diagnostic_count": 0,
        "previous_diagnostic_identities": [],
        "diagnostic_delta": 0,
        "diagnostics_changed": False,
    }
    if audit.get("passed"):
        status = "passed"
        reason = "第 0 次 audit 已通过，无需进入修复。"
    elif mode != "apply":
        status = "dry_run"
        reason = "第 0 次 audit 仍有 diagnostics，但当前 mode 不是 apply，仅记录结果。"
    else:
        status = "initial_failure"
        reason = "第 0 次 audit 未通过，第一轮 reason 必须逐条生成修复方案。"
    decision = {
        "status": status,
        "reason": reason,
        "diagnostic_count": diagnostic_count,
        "diagnostic_delta": 0,
        "changed": False,
        "diagnostic_identities": identities,
    }
    return observation, decision


def audit_target(root: Path, target: dict[str, Any]) -> dict[str, Any]:
    target_path = Path(str(target.get("path", ""))).expanduser().resolve()
    if not target_path.exists():
        audit = {
            "target_path": str(target_path),
            "returncode": 1,
            "passed": False,
            "diagnostics": [
                {
                    "code": "LGWF_TARGET_MISSING",
                    "message": "目标 .lgwf 文件不存在。",
                    "location": {"path": str(target_path), "line": 1, "column": 1},
                }
            ],
            "status": "failed",
        }
    else:
        audit = run_lgwf_audit(target_path)
        audit["status"] = "completed"
    route = "finalize" if audit.get("passed") or str(target.get("mode", "dry_run")) != "apply" else "repair"
    observation, decision = initial_repair_feedback(root, target, audit)
    write_json(root / ".lgwf" / "current_target_audit.json", audit)
    write_json(root / ".lgwf" / "repair_observation.json", observation)
    return {"audit": audit, "route": route, "observation": observation, "repair_decision": decision}


def main() -> None:
    result = audit_target(Path.cwd(), _read_payload())
    print(
        json.dumps(
            {
                "wf_audit_fix.current_audit": result["audit"],
                "wf_audit_fix.repair_route": result["route"],
                "wf_audit_fix.repair_observation": result["observation"],
                "wf_audit_fix.repair_decision": result["repair_decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
