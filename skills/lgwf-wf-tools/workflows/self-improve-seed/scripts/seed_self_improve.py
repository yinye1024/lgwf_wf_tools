from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


SCRIPT_TEMPLATES: dict[str, str] = {
    "_paths.py": r'''from __future__ import annotations

from pathlib import Path


def find_workflow_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "self-improve" / "manifest.json").is_file():
            return candidate
    raise RuntimeError(f"cannot find workflow root from {current}")


def workflow_source() -> Path:
    package_source = WORKFLOW_ROOT / "wf" / "workflow.lgwf"
    root_source = WORKFLOW_ROOT / "workflow.lgwf"
    if package_source.is_file():
        return package_source
    if root_source.is_file():
        return root_source
    raise FileNotFoundError(f"cannot find workflow.lgwf under {WORKFLOW_ROOT}")


WORKFLOW_ROOT = find_workflow_root()
SELF_IMPROVE_ROOT = WORKFLOW_ROOT / "self-improve"
LOCAL_SELF_IMPROVE = WORKFLOW_ROOT / ".local" / "self-improve"
''',
    "self_improve.py": r'''from __future__ import annotations

import subprocess
import sys

from _paths import SELF_IMPROVE_ROOT, WORKFLOW_ROOT


COMMANDS = {
    "incident": "record_incident.py",
    "proposal": "create_proposal.py",
    "scorecard": "generate_scorecard.py",
    "eval": "run_self_evals.py",
    "trace-eval": "run_trace_eval.py",
    "check": "check_self_improve.py",
}


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "help"}:
        print("usage: python self-improve/scripts/self_improve.py <incident|proposal|scorecard|eval|trace-eval|check> [args...]")
        return 0 if args else 2
    command = args.pop(0)
    script_name = COMMANDS.get(command)
    if script_name is None:
        print(f"unknown self-improve command: {command}", file=sys.stderr)
        return 2
    script = SELF_IMPROVE_ROOT / "scripts" / script_name
    completed = subprocess.run([sys.executable, str(script), *args], cwd=WORKFLOW_ROOT)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
''',
    "record_incident.py": r'''from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any

from _paths import LOCAL_SELF_IMPROVE


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "incident"


def read_evidence(raw: str) -> Any:
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("--evidence-json must be a JSON array")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["routing", "monitoring", "approval", "input_contract", "reporting", "release", "docs", "runtime", "quality"])
    parser.add_argument("--summary", required=True)
    parser.add_argument("--severity", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--evidence-json", default="[]")
    parser.add_argument("--expected-behavior", default="")
    parser.add_argument("--actual-behavior", default="")
    parser.add_argument("--suspected-area", default="")
    parser.add_argument("--follow-up", default="create_proposal", choices=["none", "add_eval", "create_proposal"])
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    incident_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{slugify(args.summary)}"
    incident = {
        "id": incident_id,
        "created_at": now.isoformat(),
        "type": args.type,
        "severity": args.severity,
        "summary": args.summary,
        "evidence": read_evidence(args.evidence_json),
        "expected_behavior": args.expected_behavior,
        "actual_behavior": args.actual_behavior,
        "suspected_area": args.suspected_area,
        "follow_up": args.follow_up,
    }
    output = LOCAL_SELF_IMPROVE / "incidents" / f"{incident_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(incident, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"incident": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    "create_proposal.py": r'''from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _paths import LOCAL_SELF_IMPROVE


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:48] or "proposal"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def default_trace_eval_report() -> dict[str, Any] | None:
    path = LOCAL_SELF_IMPROVE / "reports" / "latest-trace-eval.json"
    return read_json(path) if path.is_file() else None


def trace_failed_checks(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []
    checks = report.get("failed_checks", [])
    return [item for item in checks if isinstance(item, dict)] if isinstance(checks, list) else []


def render_trace_eval(report: dict[str, Any] | None) -> list[str]:
    if not report:
        return ["- trace_eval_report: `not_found`"]
    lines = [
        f"- trace_eval_passed: `{report.get('passed')}`",
        f"- run_id: `{report.get('run_id', '')}`",
        f"- trace_path: `{report.get('trace_path', '')}`",
        f"- eval_suite_path: `{report.get('eval_suite_path', '')}`",
    ]
    failed = trace_failed_checks(report)
    if not failed:
        lines.append("- 当前 trace eval 未发现失败 check。")
        return lines
    for check in failed:
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
        lines.append(
            "  - "
            f"destructive `{check.get('involves_destructive')}` "
            f"forbidden_permission `{check.get('involves_forbidden_permission')}` "
            f"unexpected_route `{check.get('involves_unexpected_route')}`"
        )
    return lines


def render_proposal(topic: str, source_path: Path, source: dict[str, Any], trace_eval_report: dict[str, Any] | None) -> str:
    summary = source.get("summary") or source.get("id") or topic
    lines = [
        f"# Self Improve Proposal: {topic}",
        "",
        "## 证据",
        "",
        f"- source_path: `{source_path}`",
        f"- summary: {summary}",
        "",
        "## Trace Eval Evidence",
        "",
        *render_trace_eval(trace_eval_report),
        "",
        "## 根因判断",
        "",
        f"- suspected_area: `{source.get('suspected_area', 'unknown')}`",
        "- 需要人工复核具体根因；本文件只作为提案起点。",
        "",
        "## 拟修改范围",
        "",
        "- 候选文件：目标 workflow 的 `AGENTS.md`、`wf/**`、测试或 self-improve eval case。",
        "- 不自动修改业务文件；执行前必须由用户明确批准。",
        "",
        "## 验证方式",
        "",
        "- `python self-improve/scripts/self_improve.py check`",
        "- `python self-improve/scripts/self_improve.py trace-eval`",
        "- 如涉及运行行为，补充目标 workflow 自己的测试或审计命令。",
        "",
        "## 决策",
        "",
        "- `approve`: 允许按本 proposal 进入普通修改流程。",
        "- `reject`: 不应用修改，只保留记录。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--incident", required=True)
    parser.add_argument("--topic")
    parser.add_argument("--trace-eval-report")
    args = parser.parse_args()

    source_path = Path(args.incident)
    source = read_json(source_path)
    trace_eval_report = read_json(Path(args.trace_eval_report)) if args.trace_eval_report else default_trace_eval_report()
    topic = args.topic or str(source.get("summary") or source.get("id") or "self-improve")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output = LOCAL_SELF_IMPROVE / "proposals" / f"{stamp}-{slugify(topic)}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_proposal(topic, source_path, source, trace_eval_report), encoding="utf-8")
    print(json.dumps({"proposal": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
''',
    "generate_scorecard.py": r'''from __future__ import annotations

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
''',
    "run_self_evals.py": r'''from __future__ import annotations

import json
from datetime import datetime, timezone

from _paths import LOCAL_SELF_IMPROVE, SELF_IMPROVE_ROOT, WORKFLOW_ROOT


def main() -> int:
    checks = [
        {"label": "manifest_exists", "passed": (SELF_IMPROVE_ROOT / "manifest.json").is_file()},
        {"label": "agents_exists", "passed": (WORKFLOW_ROOT / "AGENTS.md").is_file()},
        {"label": "baseline_cases_exists", "passed": (SELF_IMPROVE_ROOT / "evals" / "baseline-cases.json").is_file()},
        {"label": "entrypoint_exists", "passed": (SELF_IMPROVE_ROOT / "scripts" / "self_improve.py").is_file()},
        {"label": "trace_eval_exists", "passed": (SELF_IMPROVE_ROOT / "scripts" / "run_trace_eval.py").is_file()},
        {"label": "check_exists", "passed": (SELF_IMPROVE_ROOT / "scripts" / "check_self_improve.py").is_file()},
    ]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }
    output = LOCAL_SELF_IMPROVE / "reports" / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-self-eval.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "report": str(output)}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
''',
    "run_trace_eval.py": r'''from __future__ import annotations

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
    work_dir = LOCAL_SELF_IMPROVE / "trace-eval-workdir"
    compiled = source.parent / ".lgwf-self-improve-workflow.json"
    now = stamp()

    try:
        compile_workflow(source, compiled)
        run_id = run_workflow(compiled, work_dir)
        run_dir = work_dir / ".lgwf" / "runs" / run_id
        trace_path = run_dir / "trace.json"
        cases_dir = prepare_cases(trace_path)
        suite = run_eval_suite(work_dir, run_id, cases_dir)
        failed_cases, failed_checks = flatten_failures(suite)
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": bool(suite.get("passed")),
            "workflow_lgwf": str(source),
            "work_dir": str(work_dir),
            "run_id": run_id,
            "trace_path": str(trace_path),
            "eval_suite_path": str(run_dir / "eval-suite.json"),
            "cases_dir": str(cases_dir),
            "summary": suite.get("summary", {}),
            "failed_cases": failed_cases,
            "failed_checks": failed_checks,
            "risk_summary": risk_summary(failed_checks),
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
    finally:
        compiled.unlink(missing_ok=True)

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
''',
    "check_self_improve.py": r'''from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _paths import LOCAL_SELF_IMPROVE, SELF_IMPROVE_ROOT, WORKFLOW_ROOT


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_script(name: str) -> dict[str, Any]:
    script = SELF_IMPROVE_ROOT / "scripts" / name
    completed = subprocess.run([sys.executable, str(script)], cwd=WORKFLOW_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    payload: dict[str, Any] = {}
    stdout = completed.stdout.strip()
    if stdout:
        try:
            data = json.loads(stdout.splitlines()[-1])
            if isinstance(data, dict):
                payload = data
        except json.JSONDecodeError:
            payload = {}
    return {"script": name, "returncode": completed.returncode, "stdout": stdout, "stderr": completed.stderr.strip(), "payload": payload}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [f"# Self Improve Check {status}", "", f"- generated_at: `{report['generated_at']}`", "", "## Steps", ""]
    for step in report["steps"]:
        marker = "PASS" if step["returncode"] == 0 else "FAIL"
        lines.append(f"- `{marker}` `{step['script']}` returncode `{step['returncode']}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    steps = [run_script("run_self_evals.py"), run_script("run_trace_eval.py"), run_script("generate_scorecard.py")]
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "passed": all(step["returncode"] == 0 for step in steps), "steps": steps}
    base = LOCAL_SELF_IMPROVE / "reports" / f"{stamp()}-check"
    write_json(base.with_suffix(".json"), report)
    write_markdown(base.with_suffix(".md"), report)
    print(json.dumps({"passed": report["passed"], "json": str(base.with_suffix(".json")), "md": str(base.with_suffix(".md"))}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
''',
}


TRACE_EVAL_FILES: dict[str, str] = {
    "workflow.json": r'''{
  "nodes": [],
  "edges": [],
  "routes": [],
  "entry_point": null,
  "note": "Template marker only. run_trace_eval.py compiles the target workflow.lgwf at runtime."
}
''',
    "golden_cases/runtime_trace_contract/case.json": r'''{
  "version": 1,
  "case_id": "runtime_trace_contract",
  "description": "验证目标 workflow 能生成 trace.json 和 eval-suite.json，并完成最小 runtime smoke contract。",
  "tags": ["self-improve", "trace", "runtime-contract"],
  "kind": "runtime_contract"
}
''',
    "golden_cases/runtime_trace_contract/spec.json": r'''{
  "version": 1,
  "trajectory": {
    "status": "completed",
    "required_events": ["workflow.started", "workflow.completed"],
    "no_failed_nodes": true
  },
  "policy": {
    "allowed_error_codes": []
  },
  "metadata": {
    "purpose": "seeded_workflow_runtime_smoke"
  }
}
''',
    "golden_cases/runtime_trace_contract/golden_trace.json": r'''{
  "version": 1,
  "run_id": "template",
  "status": "completed",
  "workflow": {"source": "dynamic", "name": "external", "version": null},
  "started_at": "2026-01-01T00:00:00+00:00",
  "finished_at": "2026-01-01T00:00:01+00:00",
  "dsl_summary": {},
  "events": [],
  "nodes": [],
  "routes": [],
  "client_calls": [],
  "token_usage": {"steps": [], "totals": {}},
  "change_summary": {},
  "failure_summary": null
}
''',
}


def resolve_target_root(target: Path) -> Path:
    target = target.expanduser().resolve()
    if target.is_file() and target.name == "workflow.lgwf":
        return target.parent.parent if target.parent.name == "wf" else target.parent
    if (target / "wf" / "workflow.lgwf").is_file() or (target / "workflow.lgwf").is_file():
        return target
    raise ValueError(f"无法解析目标 workflow package: {target}")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def seed_self_improve(target: Path, *, force: bool = False) -> dict[str, Any]:
    target_root = resolve_target_root(target)
    module_root = target_root / "self-improve"
    if module_root.exists():
        if not force:
            raise FileExistsError(f"self-improve already exists: {module_root}")
        shutil.rmtree(module_root)

    workflow_name = target_root.name
    manifest = {
        "version": 2,
        "name": f"{workflow_name}-self-improve",
        "entrypoint": "scripts/self_improve.py",
        "local_state_root": ".local/self-improve",
        "commands": {
            "incident": "scripts/record_incident.py",
            "proposal": "scripts/create_proposal.py",
            "scorecard": "scripts/generate_scorecard.py",
            "eval": "scripts/run_self_evals.py",
            "trace-eval": "scripts/run_trace_eval.py",
            "check": "scripts/check_self_improve.py",
        },
        "release_policy": {"must_preserve": [".local"]},
    }
    write_text(module_root / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    write_text(
        module_root / "AGENTS.md",
        f"""# {workflow_name} Self Improve

本目录为目标 workflow 的自包含自我提升模块。它依赖当前 workflow package、Python 标准库，以及当前 Python 环境可用的 `lgwf_dsl` / `lgwf_client`。

## 使用边界

- 真实问题经用户确认后，使用 `incident` 记录。
- proposal 只生成可审查提案，不自动修改 workflow。
- `trace-eval` 运行目标 `workflow.lgwf`，基于 `trace.json` 和 `eval-suite.json` 生成运行证据。
- `.local/self-improve/` 是运行期历史，发布或复制模板时必须保留用户已有历史。
""",
    )
    write_text(
        module_root / "README.md",
        f"""# {workflow_name} 自我提升模块

常用命令：

```powershell
python self-improve/scripts/self_improve.py eval
python self-improve/scripts/self_improve.py trace-eval
python self-improve/scripts/self_improve.py check
python self-improve/scripts/self_improve.py incident --type runtime --summary "..." --evidence-json "[]"
python self-improve/scripts/self_improve.py proposal --incident <incident.json>
python self-improve/scripts/self_improve.py scorecard
```

`eval` 检查自我提升结构；`trace-eval` 运行目标 workflow 并生成 `trace.json` / `eval-suite.json` evidence；`check` 串联二者并刷新 scorecard。
""",
    )
    write_text(
        module_root / "evals" / "baseline-cases.json",
        json.dumps(
            {
                "version": 1,
                "cases": [
                    {
                        "id": "self-improve-structure-exists",
                        "expected": {
                            "must_exist": [
                                "self-improve/manifest.json",
                                "self-improve/scripts/self_improve.py",
                                "self-improve/scripts/run_trace_eval.py",
                                "self-improve/scripts/check_self_improve.py",
                            ]
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    write_text(
        module_root / "templates" / "proposal.template.md",
        """# Self Improve Proposal: <topic>

## 证据

## Trace Eval Evidence

## 根因判断

## 拟修改范围

## 验证方式

## 决策
""",
    )
    for name, content in SCRIPT_TEMPLATES.items():
        write_text(module_root / "scripts" / name, content)
    for relative, content in TRACE_EVAL_FILES.items():
        write_text(module_root / "trace-eval" / relative, content)

    for relative in ("incidents", "reports", "proposals", "scorecards", "trace-eval-cases"):
        (target_root / ".local" / "self-improve" / relative).mkdir(parents=True, exist_ok=True)

    return {"target_root": target_root, "module_root": module_root}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="给目标 workflow 播种一套自包含 self-improve 结构。")
    parser.add_argument("--target", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = seed_self_improve(Path(args.target), force=args.force)
    except Exception as exc:
        print(f"seed self-improve failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({key: str(value) for key, value in result.items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
