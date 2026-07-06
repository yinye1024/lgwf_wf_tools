from __future__ import annotations

from pathlib import Path
import sys

WF_ROOT = Path(__file__).resolve().parents[2]
if str(WF_ROOT) not in sys.path:
    sys.path.insert(0, str(WF_ROOT))

from shared.scripts.upgrade_helpers import dump_state_updates, load_runtime_payload, read_json, write_json


def run_batch_audit(payload: dict) -> tuple[dict, dict]:
    work_dir = Path(payload.get("work_dir", "."))
    manifest = read_json(work_dir / ".lgwf/target_manifest.json", {"targets": []})
    results = []
    for target in manifest.get("targets", []):
        results.append(
            {
                "target": target,
                "status": "placeholder",
                "diagnostics": [],
                "summary": "初稿阶段未接入真实 audit，保留结构化占位。",
            }
        )
    stats = {
        "target_count": len(results),
        "success_count": 0,
        "failure_count": 0,
        "placeholder_count": len(results),
    }
    return {"targets": results}, stats


def main() -> None:
    payload = load_runtime_payload("work_dir")
    work_dir = Path(payload.get("work_dir", "."))
    result, stats = run_batch_audit(payload)
    write_json(work_dir / ".lgwf/batch_audit_result.json", result)
    write_json(work_dir / ".lgwf/batch_audit_stats.json", stats)
    dump_state_updates(
        {
            "lgwf_wf_dsl_upgrade.batch_audit_result": result,
            "lgwf_wf_dsl_upgrade.batch_audit_stats": stats,
        }
    )


if __name__ == "__main__":
    main()
