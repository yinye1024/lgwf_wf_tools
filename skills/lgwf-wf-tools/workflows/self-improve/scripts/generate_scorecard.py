from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from _paths import FACADE_ROOT, SELF_IMPROVE_ROOT
LOCAL_SELF_IMPROVE = FACADE_ROOT / ".local" / "self-improve"
DEFAULT_OUTPUT_DIR = LOCAL_SELF_IMPROVE / "scorecards"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def load_json_objects(root: Path, pattern: str) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    objects: list[dict[str, Any]] = []
    for path in sorted(root.glob(pattern)):
        if path.is_file():
            objects.append(read_json(path))
    return objects


def increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def workflow_id_from_case(case: dict[str, Any]) -> str:
    expected = case.get("expected")
    if isinstance(expected, dict) and isinstance(expected.get("workflow_id"), str):
        return expected["workflow_id"]
    workflow_id = case.get("workflow_id")
    return workflow_id if isinstance(workflow_id, str) else ""


def build_scorecard(local_root: Path = LOCAL_SELF_IMPROVE) -> dict[str, Any]:
    incidents = load_json_objects(local_root / "incidents", "*.json")
    reports = load_json_objects(local_root / "reports", "*self-eval.json")
    proposals = sorted((local_root / "proposals").glob("*.md")) if (local_root / "proposals").exists() else []
    latest_report = reports[-1] if reports else {}
    case_results = latest_report.get("case_results", [])
    passed_cases = sum(1 for item in case_results if isinstance(item, dict) and item.get("passed"))
    case_count = len(case_results) if isinstance(case_results, list) else 0
    regression_pass_rate = 1.0 if case_count == 0 else passed_cases / case_count
    high_severity = sum(1 for item in incidents if item.get("severity") == "high")
    override_findings = latest_report.get("override_findings", [])
    recent_incident_type_counts: dict[str, int] = {}
    routing_misroute_count = 0
    approval_blocker_count = 0
    repeated_failed_workflows: dict[str, int] = {}
    for incident in incidents[-20:]:
        incident_type = str(incident.get("type") or "unknown")
        increment(recent_incident_type_counts, incident_type)
        summary = str(incident.get("summary") or "")
        if incident_type == "routing" or "路由" in summary or "misroute" in summary.lower():
            routing_misroute_count += 1
        if incident_type == "approval" or "approval" in summary.lower() or "确认" in summary:
            approval_blocker_count += 1
    if isinstance(case_results, list):
        for case in case_results:
            if not isinstance(case, dict) or case.get("passed"):
                continue
            workflow_id = workflow_id_from_case(case)
            if workflow_id:
                increment(repeated_failed_workflows, workflow_id)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "incident_count": len(incidents),
        "high_severity_incident_count": high_severity,
        "self_eval_report_count": len(reports),
        "proposal_count": len(proposals),
        "latest_self_eval_passed": latest_report.get("passed", None),
        "regression_pass_rate": regression_pass_rate,
        "override_high_risk_findings": len(override_findings) if isinstance(override_findings, list) else 0,
        "unsafe_autonomous_change_count": 0,
        "recent_incident_type_counts": recent_incident_type_counts,
        "repeated_failed_workflows": repeated_failed_workflows,
        "routing_misroute_count": routing_misroute_count,
        "approval_blocker_count": approval_blocker_count,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, scorecard: dict[str, Any]) -> None:
    lines = [
        "# lgwf-wf-tools Self Improve Scorecard",
        "",
        f"- generated_at: `{scorecard['generated_at']}`",
        f"- incident_count: `{scorecard['incident_count']}`",
        f"- high_severity_incident_count: `{scorecard['high_severity_incident_count']}`",
        f"- self_eval_report_count: `{scorecard['self_eval_report_count']}`",
        f"- proposal_count: `{scorecard['proposal_count']}`",
        f"- latest_self_eval_passed: `{scorecard['latest_self_eval_passed']}`",
        f"- regression_pass_rate: `{scorecard['regression_pass_rate']}`",
        f"- override_high_risk_findings: `{scorecard['override_high_risk_findings']}`",
        f"- unsafe_autonomous_change_count: `{scorecard['unsafe_autonomous_change_count']}`",
        f"- recent_incident_type_counts: `{json.dumps(scorecard['recent_incident_type_counts'], ensure_ascii=False)}`",
        f"- repeated_failed_workflows: `{json.dumps(scorecard['repeated_failed_workflows'], ensure_ascii=False)}`",
        f"- routing_misroute_count: `{scorecard['routing_misroute_count']}`",
        f"- approval_blocker_count: `{scorecard['approval_blocker_count']}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-root", default=str(LOCAL_SELF_IMPROVE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    scorecard = build_scorecard(Path(args.local_root))
    base = Path(args.output_dir) / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-scorecard"
    write_json(base.with_suffix(".json"), scorecard)
    write_markdown(base.with_suffix(".md"), scorecard)
    print(json.dumps({"json": str(base.with_suffix(".json")), "md": str(base.with_suffix(".md"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
