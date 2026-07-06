from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, load_runtime_payload, read_json, write_json


def render_summary(payload: dict) -> tuple[dict, str]:
    work_dir = Path(payload.get("work_dir", "."))
    summary = {
        "mode": payload.get("mode", "dry_run"),
        "target_manifest": read_json(work_dir / ".lgwf/target_manifest.json", {}),
        "classification_summary": read_json(work_dir / ".lgwf/classification_summary.json", {}),
        "upgrade_plan_summary": read_json(work_dir / ".lgwf/upgrade_plan_summary.json", {}),
        "approval": read_json(work_dir / ".lgwf/upgrade_plan_approval.json", {}),
        "applied_changes": read_json(work_dir / ".lgwf/applied_changes.json", {}),
        "post_upgrade_diff_summary": read_json(work_dir / ".lgwf/post_upgrade_diff_summary.json", {}),
        "status": "draft",
    }
    report = "\n".join(
        [
            "# wf-dsl-upgrade 报告",
            "",
            f"- mode: {summary['mode']}",
            f"- 目标数量: {len(summary.get('target_manifest', {}).get('targets', []))}",
            f"- 自动计划数: {summary.get('upgrade_plan_summary', {}).get('plan_count', 0)}",
            f"- 审批结果: {summary.get('approval', {}).get('decision', 'unknown')}",
            "",
            "本报告为初稿占位，后续需要接入真实 audit、规则表与写入结果。",
        ]
    )
    return summary, report


def main() -> None:
    payload = load_runtime_payload("work_dir", "mode")
    work_dir = Path(payload.get("work_dir", "."))
    summary, report = render_summary(payload)
    write_json(work_dir / ".lgwf/result_summary.json", summary)
    report_path = work_dir / "reports/wf-dsl-upgrade/report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report + "\n", encoding="utf-8")
    dump_state_updates({"lgwf_wf_dsl_upgrade.result_summary": summary})


if __name__ == "__main__":
    main()
