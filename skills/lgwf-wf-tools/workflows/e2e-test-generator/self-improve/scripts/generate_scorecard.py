from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _paths import LOCAL_SELF_IMPROVE


def count_files(name: str, pattern: str) -> int:
    root = LOCAL_SELF_IMPROVE / name
    return len(list(root.glob(pattern))) if root.exists() else 0


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else None


def trace_eval_summary(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {"available": False}
    failed_cases = report.get("failed_cases", [])
    failed_checks = report.get("failed_checks", [])
    risk_summary = report.get("risk_summary", {})
    return {
        "available": True,
        "passed": report.get("passed"),
        "run_id": report.get("run_id"),
        "trace_path": report.get("trace_path"),
        "eval_suite_path": report.get("eval_suite_path"),
        "failed_case_count": len(failed_cases) if isinstance(failed_cases, list) else 0,
        "failed_check_count": len(failed_checks) if isinstance(failed_checks, list) else 0,
        "destructive_policy_failure_count": risk_summary.get("destructive_policy_failure_count", 0) if isinstance(risk_summary, dict) else 0,
        "forbidden_permission_failure_count": risk_summary.get("forbidden_permission_failure_count", 0) if isinstance(risk_summary, dict) else 0,
        "unexpected_route_failure_count": risk_summary.get("unexpected_route_failure_count", 0) if isinstance(risk_summary, dict) else 0,
        "failed_cases": failed_cases if isinstance(failed_cases, list) else [],
        "failed_checks": failed_checks if isinstance(failed_checks, list) else [],
    }


def main() -> int:
    trace_report = read_json(LOCAL_SELF_IMPROVE / "reports" / "latest-trace-eval.json")
    scorecard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "incident_count": count_files("incidents", "*.json"),
        "proposal_count": count_files("proposals", "*.md"),
        "report_count": count_files("reports", "*.json"),
        "trace_eval": trace_eval_summary(trace_report),
    }
    output = LOCAL_SELF_IMPROVE / "scorecards" / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-scorecard.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scorecard": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
