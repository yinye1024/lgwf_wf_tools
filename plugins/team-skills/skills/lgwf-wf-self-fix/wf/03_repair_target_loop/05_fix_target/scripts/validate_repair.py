from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state, run_lgwf, write_json


Completed = Any
RunLgwf = Callable[..., Completed]
CompileAll = Callable[[Path], Completed]


def _result_to_check(name: str, command: list[str], result: Completed) -> dict[str, Any]:
    return {
        "check": name,
        "command": command,
        "returncode": int(getattr(result, "returncode", 1)),
        "stdout": getattr(result, "stdout", "") or "",
        "stderr": getattr(result, "stderr", "") or "",
    }


def _run_compileall(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "compileall", "-q", str(path)],
        text=True,
        capture_output=True,
        timeout=120,
    )


def validate_target_repair(
    target: dict[str, Any],
    *,
    run_lgwf_func: RunLgwf = run_lgwf,
    compileall_func: CompileAll = _run_compileall,
) -> dict[str, Any]:
    workflow = Path(str(target.get("target_workflow_lgwf") or ""))
    package_root = Path(str(target.get("target_package_root") or workflow.parent))
    checks: list[dict[str, Any]] = []

    audit_command = ["audit", str(workflow)]
    checks.append(_result_to_check("audit", audit_command, run_lgwf_func(audit_command, timeout=120)))

    compile_command = ["compile", str(workflow)]
    checks.append(_result_to_check("compile", compile_command, run_lgwf_func(compile_command, timeout=120)))

    py_files = list(package_root.rglob("*.py")) if package_root.exists() else []
    if py_files:
        compileall_command = [sys.executable, "-m", "compileall", "-q", str(package_root)]
        checks.append(_result_to_check("compileall", compileall_command, compileall_func(package_root)))

    issues = [
        {
            "check": check["check"],
            "command": check["command"],
            "returncode": check["returncode"],
            "stdout": check["stdout"],
            "stderr": check["stderr"],
        }
        for check in checks
        if check["returncode"] != 0
    ]
    return {
        "passed": not issues,
        "checks": checks,
        "issues": issues,
        "commands": [check["command"] for check in checks],
    }


def main() -> None:
    target = load_self_fix_target()
    validation = validate_target_repair(target)
    write_json(lgwf_dir() / "target_repair_validation.json", validation)
    append_history({"event": "repair_validated", "passed": validation["passed"], "issues": validation["issues"]})
    output_state({"target_repair_validation": validation, "repair_validation_passed": validation["passed"]})


if __name__ == "__main__":
    main()
