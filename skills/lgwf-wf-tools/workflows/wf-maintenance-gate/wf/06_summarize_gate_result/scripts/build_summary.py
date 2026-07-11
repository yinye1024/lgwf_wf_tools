from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import derive_gate_status, read_json, write_json


def main() -> None:
    root = Path.cwd()
    lgwf_dir = root / ".lgwf"
    request = read_json(lgwf_dir / "maintenance_gate_request.json")
    impact = read_json(lgwf_dir / "impact_classification.json")
    results = read_json(lgwf_dir / "verification_results.json")
    failure_routes = read_json(lgwf_dir / "failure_routes.json")

    passed = [item.get("check_id") for item in results.get("commands", []) if isinstance(item, dict) and item.get("status") == "pass"]
    failed = [item.get("check_id") for item in results.get("commands", []) if isinstance(item, dict) and item.get("status") == "fail"]
    skipped = [item.get("check_id") for item in results.get("skipped", []) if isinstance(item, dict)]
    status = derive_gate_status(
        results,
        impact.get("ambiguities", []) if isinstance(impact.get("ambiguities"), list) else [],
        skipped if str(impact.get("risk", "low")) == "high" and skipped else [],
    )

    next_actions = []
    if status == "pass":
        next_actions.append("可以继续本地维护流程；如需正式打包，仍需显式确认 package smoke。")
    elif status == "fail":
        next_actions.append("存在失败检查，先处理失败项再继续维护或发布。")
    else:
        next_actions.append("存在歧义、超时或高风险跳过项，建议人工复核。")
    for route in failure_routes.get("routes", []):
        if isinstance(route, dict):
            next_actions.append(f"建议路由到 {route.get('route')}：{route.get('reason')}")

    artifact_paths = ["reports/wf-maintenance-gate/report.md"]
    for item in results.get("commands", []):
        if isinstance(item, dict):
            artifact_paths.extend(str(path) for path in item.get("artifact_paths", []) if path)

    summary = {
        "status": status,
        "risk": impact.get("risk", "medium"),
        "input_summary": request,
        "impact_summary": {
            "categories": impact.get("categories", []),
            "impacted_workflows": impact.get("impacted_workflows", []),
            "ambiguities": impact.get("ambiguities", []),
        },
        "verification_summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "stopped_early": bool(results.get("stopped_early", False)),
        },
        "artifact_paths": artifact_paths,
        "failure_routes": failure_routes.get("routes", []),
        "next_actions": next_actions,
    }
    write_json(lgwf_dir / "maintenance_gate_summary.json", summary)
    print(
        json.dumps(
            {"wf_maintenance_gate.maintenance_gate_summary": summary},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
