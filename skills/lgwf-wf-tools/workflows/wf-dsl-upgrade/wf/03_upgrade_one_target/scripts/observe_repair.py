from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dsl_upgrade_common import (
    compute_sha256,
    diagnostic_identity,
    load_json,
    path_is_authorized,
    run_lgwf_audit,
    write_json,
)


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


def _repair_target(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    context = load_json(root / ".lgwf" / "current_target_context.json", {})
    target = context if isinstance(context, dict) else {}
    merged = dict(target)
    for key, value in payload.items():
        if value not in (None, ""):
            merged[key] = value
    return merged


def observe_repair(root: Path, target: dict[str, Any]) -> dict[str, Any]:
    target = _repair_target(root, target)
    target_path = Path(str(target.get("path", ""))).expanduser().resolve()
    allowed_dirs = [Path(str(item)).expanduser().resolve() for item in target.get("allowed_dirs", [])]
    authorized = target_path.exists() and target_path.is_file() and path_is_authorized(target_path, allowed_dirs)
    previous_audit = load_json(root / ".lgwf" / "current_target_audit.json", {})
    if not isinstance(previous_audit, dict):
        previous_audit = {}
    previous_identities = _diagnostic_identities(previous_audit)
    audit = run_lgwf_audit(target_path) if target_path.exists() else {
        "target_path": str(target_path),
        "returncode": 1,
        "passed": False,
        "diagnostics": [{"code": "LGWF_TARGET_MISSING", "message": "目标 .lgwf 文件不存在。"}],
        "status": "failed",
    }
    audit["status"] = "completed" if target_path.exists() else "failed"
    diagnostics = _diagnostics(audit)
    diagnostic_identities = _diagnostic_identities(audit)
    pre_hash = str(target.get("pre_hash", "") or "")
    current_hash = str(target.get("current_hash", "") or pre_hash)
    post_hash = compute_sha256(target_path) if target_path.exists() and target_path.is_file() else ""
    changed = bool(post_hash and current_hash and post_hash != current_hash)
    diagnostic_delta = len(diagnostics) - len(previous_identities) if previous_identities else 0
    observation = {
        "authorized": authorized,
        "target_path": str(target_path),
        "mode": str(target.get("mode", "dry_run")),
        "pre_hash": pre_hash,
        "current_hash": current_hash,
        "post_hash": post_hash,
        "changed": changed,
        "passed": bool(audit.get("passed")),
        "diagnostic_count": len(diagnostics),
        "diagnostics": diagnostics,
        "diagnostic_identities": diagnostic_identities,
        "previous_diagnostic_count": len(previous_identities),
        "previous_diagnostic_identities": previous_identities,
        "diagnostic_delta": diagnostic_delta,
        "diagnostics_changed": bool(previous_identities and previous_identities != diagnostic_identities),
    }
    write_json(root / ".lgwf" / "current_target_audit.json", audit)
    write_json(root / ".lgwf" / "repair_observation.json", observation)
    return {"audit": audit, "observation": observation}


def main() -> None:
    result = observe_repair(Path.cwd(), _read_payload())
    print(
        json.dumps(
            {
                "wf_dsl_upgrade.current_audit": result["audit"],
                "wf_dsl_upgrade.repair_observation": result["observation"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
