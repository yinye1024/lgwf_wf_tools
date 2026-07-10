from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from dsl_upgrade_common import compute_sha256, path_is_authorized, run_lgwf_audit, write_json


def _read_payload() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def observe_repair(root: Path, target: dict[str, Any]) -> dict[str, Any]:
    target_path = Path(str(target.get("path", ""))).expanduser().resolve()
    allowed_dirs = [Path(str(item)).expanduser().resolve() for item in target.get("allowed_dirs", [])]
    authorized = target_path.exists() and path_is_authorized(target_path, allowed_dirs)
    audit = run_lgwf_audit(target_path) if target_path.exists() else {
        "target_path": str(target_path),
        "returncode": 1,
        "passed": False,
        "diagnostics": [{"code": "LGWF_TARGET_MISSING", "message": "目标 .lgwf 文件不存在。"}],
        "status": "failed",
    }
    audit["status"] = "completed" if target_path.exists() else "failed"
    observation = {
        "authorized": authorized,
        "post_hash": compute_sha256(target_path) if target_path.exists() else "",
        "passed": bool(audit.get("passed")),
        "diagnostic_count": len(audit.get("diagnostics", []) if isinstance(audit.get("diagnostics"), list) else []),
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
