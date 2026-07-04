from __future__ import annotations

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
