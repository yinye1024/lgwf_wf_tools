from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, load_runtime_payload, read_json, write_json


def classify(payload: dict) -> tuple[dict, dict]:
    work_dir = Path(payload.get("work_dir", "."))
    audit_result = read_json(work_dir / ".lgwf/batch_audit_result.json", {"targets": []})
    findings = []
    for item in audit_result.get("targets", []):
        findings.append(
            {
                "target": item["target"],
                "classification": "manual_review",
                "rule_id": None,
                "reason": "初稿阶段未加载真实迁移规则，默认要求人工确认。",
                "risk": "medium",
            }
        )
    summary = {
        "auto_fixable": 0,
        "manual_review": len(findings),
        "unsupported": 0,
    }
    return {"findings": findings}, summary


def main() -> None:
    payload = load_runtime_payload("work_dir")
    work_dir = Path(payload.get("work_dir", "."))
    findings, summary = classify(payload)
    write_json(work_dir / ".lgwf/classified_findings.json", findings)
    write_json(work_dir / ".lgwf/classification_summary.json", summary)
    dump_state_updates(
        {
            "lgwf_wf_dsl_upgrade.classified_findings": findings,
            "lgwf_wf_dsl_upgrade.classification_summary": summary,
        }
    )


if __name__ == "__main__":
    main()
