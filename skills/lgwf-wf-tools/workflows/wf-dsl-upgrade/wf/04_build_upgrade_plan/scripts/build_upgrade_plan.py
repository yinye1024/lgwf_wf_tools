from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, load_runtime_payload, read_json, write_json


def build_plan(payload: dict) -> tuple[dict, dict]:
    work_dir = Path(payload.get("work_dir", "."))
    findings = read_json(work_dir / ".lgwf/classified_findings.json", {"findings": []})
    plan_items = []
    for item in findings.get("findings", []):
        if item.get("classification") != "auto_fixable":
            continue
        plan_items.append(
            {
                "target_file": item["target"],
                "rule_id": item["rule_id"],
                "risk": item["risk"],
                "change_summary": "待补齐真实规则动作。",
                "expected_impact": "待补齐真实兼容性说明。",
            }
        )
    summary = {
        "mode": payload.get("mode", "dry_run"),
        "plan_count": len(plan_items),
        "empty_plan": len(plan_items) == 0,
        "reason": "第一版默认不自动推进 manual_review 项。",
    }
    return {"items": plan_items}, summary


def main() -> None:
    payload = load_runtime_payload("work_dir", "mode")
    work_dir = Path(payload.get("work_dir", "."))
    plan, summary = build_plan(payload)
    write_json(work_dir / ".lgwf/upgrade_plan.json", plan)
    write_json(work_dir / ".lgwf/upgrade_plan_summary.json", summary)
    dump_state_updates(
        {
            "lgwf_wf_dsl_upgrade.upgrade_plan": plan,
            "lgwf_wf_dsl_upgrade.upgrade_plan_summary": summary,
        }
    )


if __name__ == "__main__":
    main()
