from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dsl_upgrade_common import compute_sha256, load_json


def finalize_target(root: Path) -> dict[str, Any]:
    context = load_json(root / ".lgwf" / "current_target_context.json", {})
    audit = load_json(root / ".lgwf" / "current_target_audit.json", {})
    target_path = Path(str(context.get("path", ""))).expanduser().resolve()
    mode = str(context.get("mode", "dry_run"))
    passed = bool(audit.get("passed")) if isinstance(audit, dict) else False
    diagnostics = audit.get("diagnostics", []) if isinstance(audit, dict) else []
    if not isinstance(diagnostics, list):
        diagnostics = []
    pre_hash = str(context.get("pre_hash", "") or "")
    post_hash = compute_sha256(target_path) if target_path.exists() else ""
    changed = bool(pre_hash and post_hash and pre_hash != post_hash)
    if passed and changed:
        status = "repaired"
    elif passed:
        status = "passed"
    elif mode != "apply":
        status = "dry_run_failed"
    else:
        status = "needs_manual_review"
    result = {
        "target_id": str(context.get("target_id", "")),
        "target_path": str(target_path),
        "mode": mode,
        "status": status,
        "passed": passed,
        "changed": changed,
        "pre_hash": pre_hash,
        "post_hash": post_hash,
        "diagnostic_count": len(diagnostics),
        "diagnostics": diagnostics,
    }
    return result


def main() -> None:
    result = finalize_target(Path.cwd())
    print(json.dumps({"wf_audit_fix.current_result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
