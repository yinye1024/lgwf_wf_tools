from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _paths import LOCAL_SELF_IMPROVE, workflow_source


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_command(argv: list[str], *, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def step_result(name: str, completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "name": name,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"# Self Improve Trace Readiness {status}",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- mode: `{report['mode']}`",
        f"- workflow_lgwf: `{report['workflow_lgwf']}`",
        "",
        "## Steps",
        "",
    ]
    for step in report["steps"]:
        marker = "PASS" if step["passed"] else "FAIL"
        lines.append(f"- `{marker}` `{step['name']}` returncode `{step['returncode']}`")
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- `git-diff-brief` 的真实 runtime 包含人工 REVIEW 和 Codex 摘要节点；self-improve 默认不自动启动完整 runtime，避免无人值守卡住或产生高 token 成本。",
            "- 本检查验证 workflow source 可被 audit/compile，是生成 trace 前的静态 readiness gate。",
            "- 需要真实 runtime 证据时，应通过 `lgwf-wf-tools` 正常 rerun，并把 `.lgwf/runs/<run_id>/trace.json` 作为 incident/proposal evidence。",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    source = workflow_source()
    output_dir = LOCAL_SELF_IMPROVE / "reports"
    compiled = LOCAL_SELF_IMPROVE / "trace-eval-workdir" / "workflow.json"
    now = stamp()
    steps: list[dict[str, Any]] = []

    try:
        audit = run_command([sys.executable, "-m", "lgwf_dsl.cli", "audit", str(source)])
        steps.append(step_result("audit_workflow", audit))
        compiled.parent.mkdir(parents=True, exist_ok=True)
        compile_result = run_command(
            [sys.executable, "-m", "lgwf_dsl.cli", "compile", str(source), "-o", str(compiled)]
        )
        steps.append(step_result("compile_workflow", compile_result))
        passed = all(step["passed"] for step in steps)
        failed_checks = [
            {
                "case_id": "static_trace_readiness",
                "check_name": step["name"],
                "message": step["stderr"] or step["stdout"],
                "evidence": [],
                "node_id": None,
                "capability": None,
                "route": None,
                "client_call_id": None,
                "involves_destructive": False,
                "involves_forbidden_permission": False,
                "involves_unexpected_route": False,
            }
            for step in steps
            if not step["passed"]
        ]
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "static_trace_readiness",
            "passed": passed,
            "workflow_lgwf": str(source),
            "work_dir": str(LOCAL_SELF_IMPROVE / "trace-eval-workdir"),
            "run_id": "",
            "trace_path": "",
            "eval_suite_path": "",
            "cases_dir": str(LOCAL_SELF_IMPROVE / "trace-eval-cases"),
            "summary": {"total": len(steps), "passed": sum(1 for step in steps if step["passed"]), "failed": len(failed_checks)},
            "failed_cases": [] if passed else [{"case_id": "static_trace_readiness", "description": "workflow audit/compile readiness failed", "kind": "static_contract"}],
            "failed_checks": failed_checks,
            "risk_summary": {
                "destructive_policy_failure_count": 0,
                "forbidden_permission_failure_count": 0,
                "unexpected_route_failure_count": 0,
            },
            "steps": steps,
        }
    except Exception as exc:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "static_trace_readiness",
            "passed": False,
            "workflow_lgwf": str(source),
            "work_dir": str(LOCAL_SELF_IMPROVE / "trace-eval-workdir"),
            "run_id": "",
            "trace_path": "",
            "eval_suite_path": "",
            "cases_dir": "",
            "summary": {"total": 1, "passed": 0, "failed": 1},
            "failed_cases": [{"case_id": "static_trace_readiness", "description": "trace readiness execution failed", "kind": "static_contract"}],
            "failed_checks": [{"case_id": "static_trace_readiness", "check_name": "execution", "message": str(exc), "evidence": [], "node_id": None, "capability": None, "route": None, "client_call_id": None, "involves_destructive": False, "involves_forbidden_permission": False, "involves_unexpected_route": False}],
            "risk_summary": {"destructive_policy_failure_count": 0, "forbidden_permission_failure_count": 0, "unexpected_route_failure_count": 0},
            "steps": [],
        }

    json_path = output_dir / f"{now}-trace-eval.json"
    md_path = output_dir / f"{now}-trace-eval.md"
    latest_json = output_dir / "latest-trace-eval.json"
    latest_md = output_dir / "latest-trace-eval.md"
    write_json(json_path, report)
    write_json(latest_json, report)
    write_markdown(md_path, report)
    write_markdown(latest_md, report)
    print(json.dumps({"passed": report["passed"], "json": str(json_path), "md": str(md_path), "latest_json": str(latest_json), "latest_md": str(latest_md), "mode": report["mode"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
