from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, load_self_fix_target, output_state, run_lgwf
from target_repair_loop import check_result, load_current_artifact, write_current_artifact


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
    workspace: dict[str, Any] | None = None,
    run_lgwf_func: RunLgwf = run_lgwf,
    compileall_func: CompileAll = _run_compileall,
) -> dict[str, Any]:
    workspace = workspace or {}
    workflow = Path(str(workspace.get("candidate_workflow_lgwf") or target.get("target_workflow_lgwf") or ""))
    package_root = Path(str(workspace.get("candidate_package_root") or target.get("target_package_root") or workflow.parent))
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
        "workflow_lgwf": str(workflow),
        "package_root": str(package_root),
        "checks": checks,
        "standard_checks": [
            check_result(
                check["check"],
                check["returncode"] == 0,
                kind="static_check",
                evidence={
                    "command": check["command"],
                    "returncode": check["returncode"],
                    "stderr": check["stderr"],
                },
            )
            for check in checks
        ],
        "issues": issues,
        "commands": [check["command"] for check in checks],
    }


def main() -> None:
    root = lgwf_dir()
    target = load_self_fix_target()
    workspace = load_current_artifact(root, "workspace", {})
    if not isinstance(workspace, dict):
        workspace = {}
    validation = validate_target_repair(target, workspace=workspace)
    write_current_artifact(root, "verification", validation)
    append_history({"event": "repair_validated", "passed": validation["passed"], "issues": validation["issues"]})
    output_state({"target_repair_current_verification": validation, "repair_validation_passed": validation["passed"]})


if __name__ == "__main__":
    main()
