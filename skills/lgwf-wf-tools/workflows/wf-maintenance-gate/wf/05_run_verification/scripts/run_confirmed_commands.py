from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from maintenance_gate_common import find_workspace_root, read_json, summarize_output, write_json


def resolved_cwd(workspace_root: Path, raw_cwd: str) -> Path:
    candidate = (workspace_root / str(raw_cwd or ".")).resolve()
    candidate.relative_to(workspace_root.resolve())
    return candidate


def main() -> None:
    root = Path.cwd()
    workspace_root = find_workspace_root(root)
    lgwf_dir = root / ".lgwf"
    plan_wrapper = read_json(lgwf_dir / "verification_plan.json")
    plan = plan_wrapper.get("confirmed", plan_wrapper)
    commands = plan.get("commands", [])
    results: list[dict[str, object]] = []
    stopped_early = False
    stop_reason: str | None = None

    for command_entry in commands:
        if not isinstance(command_entry, dict):
            continue
        argv = command_entry.get("command", [])
        check_id = str(command_entry.get("check_id", "unknown"))
        start = time.perf_counter()
        timed_out = False
        failure_type = None
        return_code = None
        stdout = ""
        stderr = ""
        short_circuit_triggered = False
        try:
            if not isinstance(argv, list) or not argv:
                raise ValueError("empty command")
            cwd = resolved_cwd(workspace_root, str(command_entry.get("cwd", ".")))
            completed = subprocess.run(
                [str(item) for item in argv],
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=int(command_entry.get("timeout_seconds", 120)),
                check=False,
            )
            return_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            if completed.returncode != 0:
                failure_type = str(command_entry.get("failure_type", "test_failure"))
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            failure_type = "timeout"
        except Exception as exc:  # pragma: no cover - defensive
            stderr = str(exc)
            failure_type = "command_contract"

        duration_ms = int((time.perf_counter() - start) * 1000)
        status = "pass" if not failure_type else "fail"
        if status == "fail" and bool(command_entry.get("short_circuit", False)):
            short_circuit_triggered = True
            stopped_early = True
            stop_reason = f"{check_id}:{failure_type}"
        results.append(
            {
                "check_id": check_id,
                "status": status,
                "command": argv,
                "cwd": command_entry.get("cwd", "."),
                "return_code": return_code,
                "duration_ms": duration_ms,
                "timed_out": timed_out,
                "stdout_summary": summarize_output(stdout),
                "stderr_summary": summarize_output(stderr),
                "artifact_paths": command_entry.get("expected_artifacts", []),
                "write_effects_observed": command_entry.get("write_effects", []) if status == "pass" else [],
                "failure_type": failure_type,
                "short_circuit_triggered": short_circuit_triggered,
            }
        )
        if stopped_early:
            break

    skipped = []
    for item in plan.get("skipped_or_suggested_checks", []):
        if isinstance(item, dict):
            skipped.append({"check_id": item.get("check_id", "unknown"), "reason": item.get("reason", "")})
    for item in plan.get("blocked_commands", []):
        if isinstance(item, dict):
            skipped.append({"check_id": item.get("check_id", "unknown"), "reason": item.get("reason", "")})
    zip_conflict = plan.get("zip_conflict", {})
    if isinstance(zip_conflict, dict) and zip_conflict.get("status") == "needs_review":
        skipped.append({"check_id": "package_smoke", "reason": str(zip_conflict.get("reason", "zip_conflict"))})

    payload = {
        "artifact_kind": "verification_results",
        "commands": results,
        "skipped": skipped,
        "stopped_early": stopped_early,
        "stop_reason": stop_reason,
    }
    write_json(lgwf_dir / "verification_results.json", payload)
    print(
        json.dumps(
            {"wf_maintenance_gate.verification_results": payload},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
