from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


STATE_ROOT = "lgwf_wf_audit_fix"


def workspace_root() -> Path:
    return Path.cwd()


def lgwf_dir() -> Path:
    path = workspace_root() / ".lgwf" / "wf_audit_fix"
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def output_state(updates: dict[str, Any], *, next_key: str | None = None, route_node: str | None = None) -> None:
    payload: dict[str, Any] = {f"{STATE_ROOT}.{key}": value for key, value in updates.items()}
    if next_key is not None:
        if not route_node:
            raise ValueError("route_node is required when next_key is set")
        payload[f"__route__{route_node}"] = next_key
    print(json.dumps(payload, ensure_ascii=False))


def load_input() -> dict[str, Any]:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        raise SystemExit("workflow input must be a JSON object")
    return data


def package_root() -> Path:
    return Path(__file__).resolve().parents[3]


def find_repo_root() -> Path:
    current = package_root()
    for candidate in [current, *current.parents]:
        marker = candidate / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"
        if marker.exists():
            return candidate
    raise FileNotFoundError("cannot locate repository root for lgwf.py")


def lgwf_py() -> Path:
    return find_repo_root() / "skills" / "lgwf-wf-tools" / "vendor" / "lgwf-client-assist" / "scripts" / "lgwf.py"


def normalize_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (workspace_root() / path).resolve()


def ensure_workflow_file(path: Path) -> None:
    if path.name != "workflow.lgwf":
        raise ValueError("target_workflow_lgwf 必须指向 workflow.lgwf")


def ensure_safe_candidate_dir(path: Path) -> None:
    root = workspace_root().resolve()
    resolved = path.resolve()
    if root not in resolved.parents and resolved != root:
        raise ValueError("candidate 目录必须位于当前 work_dir 下")


def run_audit(target_workflow_lgwf: Path) -> dict[str, Any]:
    command = [sys.executable, str(lgwf_py()), "audit", str(target_workflow_lgwf)]
    completed = subprocess.run(command, cwd=str(find_repo_root()), text=True, capture_output=True)
    stdout_text = completed.stdout.strip()
    parsed: dict[str, Any] | None = None
    if stdout_text:
        try:
            candidate = json.loads(stdout_text)
            if isinstance(candidate, dict):
                parsed = candidate
        except json.JSONDecodeError:
            parsed = None
    result = parsed or {}
    result.setdefault("passed", completed.returncode == 0)
    result["returncode"] = completed.returncode
    result["stdout"] = completed.stdout
    result["stderr"] = completed.stderr
    result["command"] = command
    return result


def summarize_audit_result(result: dict[str, Any], *, label: str) -> dict[str, Any]:
    diagnostics = result.get("diagnostics")
    issues = diagnostics if isinstance(diagnostics, list) else []
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary:
        summary = f"{label} audit {'通过' if result.get('passed') else '失败'}"
    return {
        "label": label,
        "passed": bool(result.get("passed")),
        "issue_count": len(issues),
        "summary": summary,
        "diagnostics": issues,
        "returncode": result.get("returncode"),
    }


def append_attempt_log(entry: dict[str, Any]) -> list[dict[str, Any]]:
    path = lgwf_dir() / "candidate_attempt_log.json"
    history = read_json(path, [])
    if not isinstance(history, list):
        history = []
    event = dict(entry)
    event.setdefault("ts", datetime.now(UTC).isoformat())
    history.append(event)
    write_json(path, history)
    return history


def load_runtime_context() -> dict[str, Any]:
    data = read_json(lgwf_dir() / "runtime_context.json", {})
    return data if isinstance(data, dict) else {}


def save_runtime_context(data: dict[str, Any]) -> None:
    write_json(lgwf_dir() / "runtime_context.json", data)


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def relative_to_workspace(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace_root().resolve()))
    except ValueError:
        return str(path)
