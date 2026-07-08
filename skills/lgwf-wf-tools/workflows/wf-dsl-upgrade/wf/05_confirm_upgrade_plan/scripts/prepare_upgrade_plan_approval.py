from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, get_runtime_field, load_runtime_payload, read_json, write_json


def build_confirmation_context(payload: dict) -> dict:
    work_dir = Path(payload.get("work_dir", "."))
    manifest = read_json(work_dir / ".lgwf/target_manifest.json", {"targets": []})
    classification = read_json(work_dir / ".lgwf/classification_summary.json", {})
    plan_summary = read_json(work_dir / ".lgwf/upgrade_plan_summary.json", {})
    return {
        "mode": get_runtime_field(payload, "mode", "dry_run"),
        "target_count": len(manifest.get("targets", [])),
        "classification_summary": classification,
        "upgrade_plan_summary": plan_summary,
        "message": "apply 前必须经过人工批准；dry_run 与 reject 都不会触发真实写入。",
    }


def main() -> None:
    payload = load_runtime_payload("work_dir")
    work_dir = Path(payload.get("work_dir", "."))
    context = build_confirmation_context(payload)
    write_json(work_dir / ".lgwf/upgrade_plan_confirmation_context.json", context)
    dump_state_updates({"lgwf_wf_dsl_upgrade.upgrade_plan_confirmation_context": context})


if __name__ == "__main__":
    main()
