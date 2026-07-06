from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import (
    dump_state_updates,
    extract_decision,
    load_runtime_payload,
    read_json,
    write_json,
)


def finalize(payload: dict) -> dict:
    work_dir = Path(payload.get("work_dir", "."))
    approval = read_json(
        work_dir / ".lgwf/upgrade_plan_approval.json",
        {"decision": extract_decision(payload, "reject")},
    )
    decision = extract_decision(approval, extract_decision(payload, "reject"))
    normalized = {
        "decision": decision,
        "mode": payload.get("mode", "dry_run"),
        "allow_apply": payload.get("mode") == "apply" and decision == "approve",
    }
    return normalized


def main() -> None:
    payload = load_runtime_payload("work_dir", "mode", "decision", "approval")
    work_dir = Path(payload.get("work_dir", "."))
    normalized = finalize(payload)
    write_json(work_dir / ".lgwf/upgrade_plan_approval.json", normalized)
    dump_state_updates({"lgwf_wf_dsl_upgrade.upgrade_plan_approval": normalized})


if __name__ == "__main__":
    main()
