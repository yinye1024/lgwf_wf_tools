from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import build_verification_plan, find_workspace_root, read_json, write_json


def main() -> None:
    root = Path.cwd()
    workspace_root = find_workspace_root(root)
    lgwf_dir = root / ".lgwf"
    request = read_json(lgwf_dir / "maintenance_gate_request.json")
    impact = read_json(lgwf_dir / "impact_classification.json")
    proposal = build_verification_plan(impact, request)
    proposal["change_source"] = read_json(lgwf_dir / "change_context.json").get("change_source", "")
    output_zip = request.get("output_zip")
    if isinstance(output_zip, str) and output_zip.strip():
        zip_path = (workspace_root / output_zip).resolve()
        if zip_path.exists():
            proposal["zip_conflict"] = {
                "status": "needs_review",
                "path": output_zip,
                "reason": "output_zip 已存在，必须经 REVIEW 显式确认覆盖策略",
            }
            retained_commands = []
            for item in proposal.get("commands", []):
                if item.get("check_id") == "package_smoke":
                    proposal.setdefault("blocked_commands", []).append(
                        {
                            "check_id": "package_smoke",
                            "reason": "output_zip 已存在，等待 REVIEW 决策 use_new_path 或 allow_overwrite",
                        }
                    )
                else:
                    retained_commands.append(item)
            proposal["commands"] = retained_commands
    write_json(lgwf_dir / "verification_plan_proposal.json", proposal)
    print(
        json.dumps(
            {"wf_maintenance_gate.verification_plan_proposal": proposal},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
