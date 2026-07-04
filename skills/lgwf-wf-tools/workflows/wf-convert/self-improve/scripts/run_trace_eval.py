from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _paths import LOCAL_SELF_IMPROVE, SELF_IMPROVE_ROOT, WORKFLOW_ROOT, workflow_source


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=WORKFLOW_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def require_success(completed: subprocess.CompletedProcess[str], label: str) -> None:
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed\nstdout={completed.stdout.strip()}\nstderr={completed.stderr.strip()}")


def compile_workflow(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    completed = run_command([sys.executable, "-m", "lgwf_dsl.cli", "compile", str(source), "-o", str(output)])
    require_success(completed, "compile workflow")


def latest_run_id(work_dir: Path) -> str:
    completed = run_command([sys.executable, "-m", "lgwf_client.cli", "list-runs", "--work-dir", str(work_dir), "--limit", "1"])
    require_success(completed, "list runs")
    payload = json.loads(completed.stdout.splitlines()[0])
    runs = payload.get("runs")
    if not isinstance(runs, list) or not runs or not isinstance(runs[0], dict):
        raise RuntimeError(f"no run record found under {work_dir}")
    run_id = runs[0].get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise RuntimeError("latest run record missing run_id")
    return run_id


def run_workflow(workflow_json: Path, work_dir: Path) -> str:
    work_dir.mkdir(parents=True, exist_ok=True)
    completed = run_command([
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
    ])
    require_success(completed, "run workflow")
    return latest_run_id(work_dir)


def prepare_cases(trace_path: Path) -> Path:
    source_case = SELF_IMPROVE_ROOT / "trace-eval" / "golden_cases" / "runtime_trace_contract"
    local_case = LOCAL_SELF_IMPROVE / "trace-eval-cases" / "runtime_trace_contract"
    if local_case.exists():
        shutil.rmtree(local_case)
    local_case.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_case / "case.json", local_case / "case.json")
    shutil.copy2(source_case / "spec.json", local_case / "spec.json")
    shutil.copy2(trace_path, local_case / "golden_trace.json")
    return local_case.parent


def run_eval_suite(work_dir: Path, run_id: str, cases_dir: Path) -> dict[str, Any]:
    completed = run_command([
        sys.executable,
        "-m",
        "lgwf_client.cli",
        "eval-suite",
        "--work-dir",
        str(work_dir),
        "--run-id",
        run_id,
        "--cases-dir",
        str(cases_dir),
    ])
    require_success(completed, "eval suite")
    return json.loads(completed.stdout.splitlines()[0])


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
    return None


def flatten_failures(suite: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    failed_cases: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    cases = suite.get("cases")
    for case in cases if isinstance(cases, list) else []:
        if not isinstance(case, dict) or case.get("passed"):
            continue
        case_id = str(case.get("case_id") or "")
        failed_cases.append({"case_id": case_id, "description": case.get("description"), "kind": case.get("kind")})
        checks = case.get("checks")
        for check in checks if isinstance(checks, list) else []:
            if not isinstance(check, dict) or check.get("passed"):
                continue
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
                    **risk_flags(check),
                }
            )
    return failed_cases, failed_checks


def risk_summary(failed_checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "destructive_policy_failure_count": sum(1 for item in failed_checks if item.get("involves_destructive")),
        "forbidden_permission_failure_count": sum(1 for item in failed_checks if item.get("involves_forbidden_permission")),
        "unexpected_route_failure_count": sum(1 for item in failed_checks if item.get("involves_unexpected_route")),
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
        f"- summary: `{json.dumps(report.get('summary', {}), ensure_ascii=False)}`",
        f"- risk_summary: `{json.dumps(report.get('risk_summary', {}), ensure_ascii=False)}`",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    source = workflow_source()
    output_dir = LOCAL_SELF_IMPROVE / "reports"
    compiled = LOCAL_SELF_IMPROVE / "compiled" / "workflow.json"
    now = stamp()

    try:
        compile_workflow(source, compiled)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": True,
            "workflow_lgwf": str(source),
            "compiled_workflow_path": str(compiled),
            "work_dir": "",
            "run_id": "",
            "trace_path": "",
            "eval_suite_path": "",
            "cases_dir": "",
            "summary": {
                "compile": "passed",
                "runtime_mode": "compile_only",
                "reason": "wf-convert 包含人工确认、子 workflow 和 handoff，self-improve trace-eval 不以空输入启动完整转换流程。",
            },
            "failed_cases": [],
            "failed_checks": [],
            "risk_summary": {
                "destructive_policy_failure_count": 0,
                "forbidden_permission_failure_count": 0,
                "unexpected_route_failure_count": 0,
            },
        }
    except Exception as exc:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "workflow_lgwf": str(source),
            "work_dir": str(work_dir),
            "run_id": "",
            "trace_path": "",
            "eval_suite_path": "",
            "cases_dir": "",
            "summary": {"total": 1, "passed": 0, "failed": 1},
            "failed_cases": [{"case_id": "runtime_trace_contract", "description": "trace eval execution failed", "kind": "runtime_contract"}],
            "failed_checks": [{"case_id": "runtime_trace_contract", "check_name": "trace_eval.execution", "message": str(exc), "evidence": [], "node_id": None, "capability": None, "route": None, "client_call_id": None, "involves_destructive": False, "involves_forbidden_permission": False, "involves_unexpected_route": False}],
            "risk_summary": {"destructive_policy_failure_count": 0, "forbidden_permission_failure_count": 0, "unexpected_route_failure_count": 0},
        }
    json_path = output_dir / f"{now}-trace-eval.json"
    md_path = output_dir / f"{now}-trace-eval.md"
    latest_json = output_dir / "latest-trace-eval.json"
    latest_md = output_dir / "latest-trace-eval.md"
    write_json(json_path, report)
    write_json(latest_json, report)
    write_markdown(md_path, report)
    write_markdown(latest_md, report)
    print(json.dumps({"passed": report["passed"], "json": str(json_path), "md": str(md_path), "latest_json": str(latest_json), "latest_md": str(latest_md), "trace": report["trace_path"], "eval_suite": report["eval_suite_path"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
