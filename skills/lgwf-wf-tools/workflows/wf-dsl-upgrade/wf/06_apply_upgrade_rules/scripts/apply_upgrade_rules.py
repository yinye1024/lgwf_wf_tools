from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, load_runtime_payload, read_json, write_json


def apply_rules(payload: dict) -> tuple[dict, dict]:
    work_dir = Path(payload.get("work_dir", "."))
    approval = read_json(work_dir / ".lgwf/upgrade_plan_approval.json", {"allow_apply": False})
    plan = read_json(work_dir / ".lgwf/upgrade_plan.json", {"items": []})
    if not approval.get("allow_apply"):
        applied = {"items": [], "status": "skipped"}
        manifest = {"targets": [], "reason": "未获 apply 授权或当前为 dry_run。"}
        return applied, manifest
    items = []
    for item in plan.get("items", []):
        items.append(
            {
                "target_file": item["target_file"],
                "status": "placeholder",
                "change_summary": item["change_summary"],
                "skip_reason": "初稿阶段未接入真实规则写入。",
            }
        )
    applied = {"items": items, "status": "placeholder"}
    manifest = {"targets": [item["target_file"] for item in items]}
    return applied, manifest


def main() -> None:
    payload = load_runtime_payload("work_dir")
    work_dir = Path(payload.get("work_dir", "."))
    applied, manifest = apply_rules(payload)
    write_json(work_dir / ".lgwf/applied_changes.json", applied)
    write_json(work_dir / ".lgwf/applied_target_manifest.json", manifest)
    dump_state_updates(
        {
            "lgwf_wf_dsl_upgrade.applied_changes": applied,
            "lgwf_wf_dsl_upgrade.applied_target_manifest": manifest,
        }
    )


if __name__ == "__main__":
    main()
