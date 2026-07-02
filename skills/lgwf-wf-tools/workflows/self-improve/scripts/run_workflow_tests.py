from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from _paths import FACADE_ROOT, SELF_IMPROVE_ROOT
BASELINE_PATH = SELF_IMPROVE_ROOT / "workflow-health" / "baseline.json"
DEFAULT_OUTPUT_DIR = FACADE_ROOT / ".local" / "self-improve" / "reports"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def baseline_workflows(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    workflows = data.get("workflows")
    if not isinstance(workflows, list):
        raise ValueError("workflow-health baseline workflows must be list")
    return [item for item in workflows if isinstance(item, dict)]


def normalize_python_command(command: str) -> str:
    stripped = command.strip()
    if stripped == "python":
        return f'"{sys.executable}"'
    if stripped.startswith("python "):
        return f'"{sys.executable}" {stripped[len("python "):]}'
    return command


def run_test_command(item: dict[str, Any], *, facade_root: Path, timeout_seconds: int) -> dict[str, Any]:
    workflow_id = str(item.get("id") or "<missing>")
    command = item.get("test_command")
    if not isinstance(command, str) or not command.strip():
        return {
            "id": workflow_id,
            "passed": False,
            "returncode": 2,
            "command": "",
            "stdout": "",
            "stderr": "missing test_command",
        }
    normalized = normalize_python_command(command)
    try:
        completed = subprocess.run(
            normalized,
            cwd=facade_root,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout_seconds,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        return {
            "id": workflow_id,
            "passed": completed.returncode == 0,
            "returncode": completed.returncode,
            "command": command,
            "stdout": stdout,
            "stderr": stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "id": workflow_id,
            "passed": False,
            "returncode": 124,
            "command": command,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": f"workflow test command timed out after {timeout_seconds}s",
        }


def build_report(
    *,
    workflow_id: str | None,
    baseline_path: Path,
    facade_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    workflows = baseline_workflows(baseline_path)
    if workflow_id:
        workflows = [item for item in workflows if item.get("id") == workflow_id]
        if not workflows:
            raise ValueError(f"workflow id not found in baseline: {workflow_id}")
    results = [run_test_command(item, facade_root=facade_root, timeout_seconds=timeout_seconds) for item in workflows]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflow_id": workflow_id or "",
        "passed": all(item["passed"] for item in results),
        "workflow_count": len(results),
        "workflow_results": results,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"# lgwf-wf-tools Workflow Tests {status}",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- workflow_count: `{report['workflow_count']}`",
        "",
    ]
    for item in report["workflow_results"]:
        marker = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- `{marker}` `{item['id']}` returncode `{item['returncode']}`")
        if item.get("stderr"):
            lines.append(f"  - stderr: `{str(item['stderr'])[:500]}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow-id")
    parser.add_argument("--baseline", default=str(BASELINE_PATH))
    parser.add_argument("--facade-root", default=str(FACADE_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()

    report = build_report(
        workflow_id=args.workflow_id,
        baseline_path=Path(args.baseline),
        facade_root=Path(args.facade_root),
        timeout_seconds=args.timeout_seconds,
    )
    suffix = f"-{args.workflow_id}" if args.workflow_id else ""
    base = Path(args.output_dir) / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-workflow-tests{suffix}"
    write_json(base.with_suffix(".json"), report)
    write_markdown(base.with_suffix(".md"), report)
    print(json.dumps({"passed": report["passed"], "json": str(base.with_suffix(".json")), "md": str(base.with_suffix(".md"))}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
