from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dsl_upgrade_common import run_lgwf_audit, write_json


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


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
    write_json(root / ".lgwf" / "current_target_audit.json", audit)
    return {"audit": audit, "route": route}


def main() -> None:
    result = audit_target(Path.cwd(), _read_payload())
    print(
        json.dumps(
            {
                "wf_dsl_upgrade.current_audit": result["audit"],
                "wf_dsl_upgrade.repair_route": result["route"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
