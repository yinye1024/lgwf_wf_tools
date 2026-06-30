from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SELF_IMPROVE_ROOT = Path(__file__).resolve().parents[1]
FACADE_ROOT = SELF_IMPROVE_ROOT.parent
DEFAULT_OUTPUT_DIR = FACADE_ROOT / ".local" / "self-improve" / "pre-release"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_command(argv: list[str] | str, output_dir: Path) -> dict[str, Any]:
    if isinstance(argv, str):
        completed = subprocess.run(
            argv,
            cwd=FACADE_ROOT,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        recorded_argv: list[str] | str = argv
    else:
        completed = subprocess.run(
            [sys.executable, *argv],
            cwd=FACADE_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        recorded_argv = argv
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload: dict[str, Any] = {}
    if stdout:
        try:
            data = json.loads(stdout.splitlines()[-1])
            if isinstance(data, dict):
                payload = data
        except json.JSONDecodeError:
            payload = {}
    return {
        "argv": recorded_argv,
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "payload": payload,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"# lgwf-wf-tools Pre-release Check {status}",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- output_dir: `{report['output_dir']}`",
        "",
        "## Steps",
        "",
    ]
    for step in report["steps"]:
        marker = "PASS" if step["returncode"] == 0 else "FAIL"
        lines.append(f"- `{marker}` `{step['name']}` returncode `{step['returncode']}`")
        payload = step.get("payload") or {}
        if payload:
            lines.append(f"  - payload: `{json.dumps(payload, ensure_ascii=False)}`")
        if step.get("stderr"):
            lines.append(f"  - stderr: `{step['stderr'][:500]}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="pre-release")
    parser.add_argument("--source", default="pre-release-check")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-workflow-tests", action="store_true")
    parser.add_argument("--workflow-tests-baseline", default="self-improve/workflow-health/baseline.json")
    parser.add_argument("--workflow-tests-facade-root", default=str(FACADE_ROOT))
    parser.add_argument("--workflow-tests-timeout-seconds", type=int, default=120)
    parser.add_argument("--doctor-command", help="Override doctor command. Intended for tests.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    changed_files = output_dir / "changed-files.json"

    steps = []
    doctor_command: list[str] | str = args.doctor_command or ["scripts/doctor_lgwf_wf_tools.py"]
    commands: list[tuple[str, list[str] | str]] = [
        ("doctor", doctor_command),
        ("collect_changed_files", ["self-improve/scripts/collect_changed_files.py", "--output", str(changed_files)]),
        (
            "run_self_evals",
            [
                "self-improve/scripts/run_self_evals.py",
                "--changed-files",
                str(changed_files),
                "--check-overrides",
                "--output-dir",
                str(output_dir),
            ],
        ),
        ("workflow_health", ["self-improve/scripts/check_workflow_health.py", "--output-dir", str(output_dir)]),
    ]
    if args.run_workflow_tests:
        commands.append(
            (
                "workflow_tests",
                [
                    "self-improve/scripts/run_workflow_tests.py",
                    "--baseline",
                    args.workflow_tests_baseline,
                    "--facade-root",
                    args.workflow_tests_facade_root,
                    "--timeout-seconds",
                    str(args.workflow_tests_timeout_seconds),
                    "--output-dir",
                    str(output_dir),
                ],
            )
        )
    commands.extend(
        [
        ("generate_scorecard", ["self-improve/scripts/generate_scorecard.py", "--output-dir", str(output_dir)]),
        (
            "write_upgrade_report",
            [
                "self-improve/scripts/write_upgrade_report.py",
                "--version",
                args.version,
                "--source",
                args.source,
                "--output-dir",
                str(output_dir),
            ],
        ),
        ]
    )
    for name, argv in commands:
        result = run_command(argv, output_dir)
        result["name"] = name
        steps.append(result)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "passed": all(step["returncode"] == 0 for step in steps),
        "steps": steps,
    }
    base = output_dir / f"{utc_stamp()}-pre-release"
    write_json(base.with_suffix(".json"), report)
    write_markdown(base.with_suffix(".md"), report)
    print(json.dumps({"passed": report["passed"], "json": str(base.with_suffix(".json")), "md": str(base.with_suffix(".md"))}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
