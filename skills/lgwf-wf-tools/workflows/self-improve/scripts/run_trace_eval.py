from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from _paths import FACADE_ROOT, SELF_IMPROVE_ROOT

DEFAULT_OUTPUT_DIR = FACADE_ROOT / ".local" / "self-improve" / "reports"
DEFAULT_WORKFLOW_JSON = SELF_IMPROVE_ROOT / "trace-eval" / "workflow.json"
DEFAULT_CASES_DIR = SELF_IMPROVE_ROOT / "trace-eval" / "golden_cases"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cli(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "lgwf_client.cli", *args],
        cwd=FACADE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = completed.stdout.strip()
    payload: dict[str, Any] = {}
    if stdout:
        try:
            data = json.loads(stdout.splitlines()[0])
            if isinstance(data, dict):
                payload = data
        except json.JSONDecodeError:
            payload = {}
    if completed.returncode != 0:
        raise RuntimeError(
            f"lgwf_client.cli failed: {' '.join(args)}\nstdout={stdout}\nstderr={completed.stderr.strip()}"
        )
    return payload


def latest_run_id(work_dir: Path) -> str:
    payload = run_cli(["list-runs", "--work-dir", str(work_dir), "--limit", "1"])
    runs = payload.get("runs")
    if not isinstance(runs, list) or not runs:
        raise RuntimeError(f"no run record found under {work_dir}")
    run_id = runs[0].get("run_id") if isinstance(runs[0], dict) else None
    if not isinstance(run_id, str) or not run_id:
        raise RuntimeError(f"latest run record missing run_id under {work_dir}")
    return run_id


def run_workflow(workflow_json: Path, work_dir: Path) -> str:
    work_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "lgwf_client.cli",
            "--workflow-json",
            str(workflow_json),
            "--work-dir",
            str(work_dir),
            "--input-json",
            "{}",
            "--record",
            "true",
        ],
        cwd=FACADE_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"trace eval workflow failed: {workflow_json}\nstdout={completed.stdout.strip()}\nstderr={completed.stderr.strip()}"
        )
    return latest_run_id(work_dir)


def run_eval_suite(work_dir: Path, run_id: str, cases_dir: Path) -> dict[str, Any]:
    return run_cli(["eval-suite", "--work-dir", str(work_dir), "--run-id", run_id, "--cases-dir", str(cases_dir)])


def risk_flags(check: dict[str, Any]) -> dict[str, bool]:
    name = str(check.get("name") or "")
    message = str(check.get("message") or "")
    evidence = json.dumps(check.get("evidence", []), ensure_ascii=False)
    combined = f"{name}\n{message}\n{evidence}".lower()
    return {
        "involves_destructive": "destructive" in combined,
        "involves_forbidden_permission": "forbidden_permissions" in combined or "forbidden permission" in combined,
        "involves_unexpected_route": "forbidden_routes" in combined or "route" in combined,
    }


def first_evidence_value(evidence: Any, *keys: str) -> Any:
    if not isinstance(evidence, list):
        return None
    for item in evidence:
        if not isinstance(item, dict):
            continue
        for key in keys:
            value = item.get(key)
            if value is not None:
                return value
        route = item.get("route")
        if isinstance(route, dict):
            for key in keys:
                value = route.get(key)
                if value is not None:
                    return value
    return None


def flatten_failures(suite: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    failed_cases: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    cases = suite.get("cases")
    for case in cases if isinstance(cases, list) else []:
        if not isinstance(case, dict) or case.get("passed"):
            continue
        case_id = str(case.get("case_id") or "")
        failed_cases.append(
            {
                "case_id": case_id,
                "description": case.get("description"),
                "kind": case.get("kind"),
            }
        )
        checks = case.get("checks")
        for check in checks if isinstance(checks, list) else []:
            if not isinstance(check, dict) or check.get("passed"):
                continue
            flags = risk_flags(check)
            evidence = check.get("evidence", [])
            failed_checks.append(
                {
                    "case_id": case_id,
                    "check_name": check.get("name"),
                    "message": check.get("message"),
                    "evidence": evidence,
                    "node_id": first_evidence_value(evidence, "node_id", "source_node", "target_node"),
                    "capability": first_evidence_value(evidence, "capability"),
                    "route": first_evidence_value(evidence, "route_key"),
                    "client_call_id": first_evidence_value(evidence, "client_call_id", "instruction_id"),
                    **flags,
                }
            )
    return failed_cases, failed_checks


def risk_summary(failed_checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "destructive_policy_failure_count": sum(1 for item in failed_checks if item.get("involves_destructive")),
        "forbidden_permission_failure_count": sum(
            1 for item in failed_checks if item.get("involves_forbidden_permission")
        ),
        "unexpected_route_failure_count": sum(1 for item in failed_checks if item.get("involves_unexpected_route")),
    }


def build_report(workflow_json: Path, work_dir: Path, cases_dir: Path, run_id: str, suite: dict[str, Any]) -> dict[str, Any]:
    failed_cases, failed_checks = flatten_failures(suite)
    eval_suite_path = work_dir / ".lgwf" / "runs" / run_id / "eval-suite.json"
    trace_path = work_dir / ".lgwf" / "runs" / run_id / "trace.json"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": bool(suite.get("passed")),
        "workflow_json": str(workflow_json),
        "work_dir": str(work_dir),
        "run_id": run_id,
        "trace_path": str(trace_path),
        "eval_suite_path": str(eval_suite_path),
        "cases_dir": str(cases_dir),
        "summary": suite.get("summary", {}),
        "failed_cases": failed_cases,
        "failed_checks": failed_checks,
        "risk_summary": risk_summary(failed_checks),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"# Self Improve Trace Eval {status}",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- run_id: `{report['run_id']}`",
        f"- trace_path: `{report['trace_path']}`",
        f"- eval_suite_path: `{report['eval_suite_path']}`",
        f"- cases_dir: `{report['cases_dir']}`",
        f"- summary: `{json.dumps(report.get('summary', {}), ensure_ascii=False)}`",
        f"- risk_summary: `{json.dumps(report.get('risk_summary', {}), ensure_ascii=False)}`",
        "",
        "## Failed Checks",
        "",
    ]
    failed_checks = report.get("failed_checks", [])
    if isinstance(failed_checks, list) and failed_checks:
        for check in failed_checks:
            lines.append(
                "- "
                f"case `{check.get('case_id', '')}` check `{check.get('check_name', '')}`: "
                f"{check.get('message', '')}"
            )
            lines.append(
                "  - "
                f"node `{check.get('node_id')}` capability `{check.get('capability')}` "
                f"route `{check.get('route')}` client_call `{check.get('client_call_id')}`"
            )
    else:
        lines.append("- 无失败 check。")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--work-dir")
    parser.add_argument("--workflow-json", default=str(DEFAULT_WORKFLOW_JSON))
    parser.add_argument("--cases-dir", default=str(DEFAULT_CASES_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    stamp = utc_stamp()
    work_dir = Path(args.work_dir) if args.work_dir else output_dir / "trace-eval-workdir"
    workflow_json = Path(args.workflow_json)
    cases_dir = Path(args.cases_dir)
    if not workflow_json.is_file():
        raise FileNotFoundError(f"trace eval workflow missing: {workflow_json}")
    if not cases_dir.is_dir():
        raise FileNotFoundError(f"trace eval cases dir missing: {cases_dir}")

    run_id = run_workflow(workflow_json, work_dir)
    suite = run_eval_suite(work_dir, run_id, cases_dir)
    report = build_report(workflow_json, work_dir, cases_dir, run_id, suite)

    base = output_dir / f"{stamp}-trace-eval"
    json_path = base.with_suffix(".json")
    md_path = base.with_suffix(".md")
    latest_json = output_dir / "latest-trace-eval.json"
    latest_md = output_dir / "latest-trace-eval.md"
    write_json(json_path, report)
    write_json(latest_json, report)
    write_markdown(md_path, report)
    write_markdown(latest_md, report)
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "json": str(json_path),
                "md": str(md_path),
                "latest_json": str(latest_json),
                "latest_md": str(latest_md),
                "trace": report["trace_path"],
                "eval_suite": report["eval_suite_path"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
