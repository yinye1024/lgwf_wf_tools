from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, load_runtime_payload, read_json, write_json


def verify(payload: dict) -> tuple[dict, dict]:
    work_dir = Path(payload.get("work_dir", "."))
    applied = read_json(work_dir / ".lgwf/applied_changes.json", {"items": [], "status": "skipped"})
    modified = [item for item in applied.get("items", []) if item.get("status") == "modified"]
    result = {
        "targets": modified,
        "status": "skipped" if not modified else "placeholder",
    }
    diff_summary = {
        "modified_count": len(modified),
        "resolved_count": 0,
        "remaining_count": 0,
        "reason": "初稿阶段未接入真实 post-audit。",
    }
    return result, diff_summary


def main() -> None:
    payload = load_runtime_payload("work_dir")
    work_dir = Path(payload.get("work_dir", "."))
    result, diff_summary = verify(payload)
    write_json(work_dir / ".lgwf/post_upgrade_audit_result.json", result)
    write_json(work_dir / ".lgwf/post_upgrade_diff_summary.json", diff_summary)
    dump_state_updates(
        {
            "lgwf_wf_dsl_upgrade.post_upgrade_audit_result": result,
            "lgwf_wf_dsl_upgrade.post_upgrade_diff_summary": diff_summary,
        }
    )


if __name__ == "__main__":
    main()
