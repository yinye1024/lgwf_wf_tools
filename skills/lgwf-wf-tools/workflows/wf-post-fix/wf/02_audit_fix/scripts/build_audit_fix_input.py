from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import append_stage_result, finalize_stage_decision, load_target, output_state, resolve_workspace_path


def build_audit_fix_input(target: dict[str, Any]) -> dict[str, Any]:
    package_root = resolve_workspace_path(target["target_package_root"])
    workflow_path = resolve_workspace_path(target["target_workflow_lgwf"])
    workflow_root = package_root / "wf"
    target_path = workflow_root if workflow_root.is_dir() else workflow_path
    target_dirs = target.get("target_dirs") or [str(package_root)]
    allowed_dirs = [str(resolve_workspace_path(str(item))) for item in target_dirs]
    if str(package_root) not in allowed_dirs:
        allowed_dirs.append(str(package_root))
    return {
        "audit_fix_target": {
            "target_paths": [str(target_path)],
            "allowed_dirs": allowed_dirs,
            "mode": "apply",
            "scope_mode": "explicit",
            "max_targets": 32,
        }
    }


def main() -> None:
    decision = finalize_stage_decision("audit_fix")
    target = load_target()
    payload = build_audit_fix_input(target)
    append_stage_result("audit_fix", "ready", decision=decision)
    output_state(
        {"audit_fix_input": payload, "audit_fix_stage_decision": decision},
    )


if __name__ == "__main__":
    main()
