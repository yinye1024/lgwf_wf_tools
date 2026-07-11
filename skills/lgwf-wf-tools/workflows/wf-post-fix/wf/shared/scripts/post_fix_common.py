from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


STATE_ROOT = "lgwf_wf_post_fix"
AUTO_ALLOWED_STAGES = {
    "audit_fix",
    "prompt_fix",
    "prompt_upgrade",
    "e2e_generate",
    "script_flow_e2e",
    "runtime_fake_e2e",
}
REAL_CONFIRM_STAGES = {"real_positive_e2e", "wf_fix_positive_e2e"}
VALID_DECISIONS = {"run", "skip", "auto", "stop"}


def workspace_root() -> Path:
    return Path.cwd()


def lgwf_dir(root: Path | None = None) -> Path:
    path = (root or workspace_root()) / ".lgwf"
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


def target_path() -> Path:
    return lgwf_dir() / "post_fix_target.json"


def decisions_path() -> Path:
    return lgwf_dir() / "post_fix_decisions.json"


def stage_results_path() -> Path:
    return lgwf_dir() / "post_fix_stage_results.json"


def generated_tests_path() -> Path:
    return lgwf_dir() / "post_fix_generated_tests.json"


def load_target() -> dict[str, Any]:
    data = read_json(target_path(), {})
    if not isinstance(data, dict):
        raise ValueError(".lgwf/post_fix_target.json must contain a JSON object")
    return data


def load_decisions() -> dict[str, Any]:
    data = read_json(decisions_path(), {"auto_enabled": False, "stages": []})
    if not isinstance(data, dict):
        data = {"auto_enabled": False, "stages": []}
    if not isinstance(data.get("stages"), list):
        data["stages"] = []
    data["auto_enabled"] = bool(data.get("auto_enabled"))
    return data


def save_decisions(data: dict[str, Any]) -> None:
    write_json(decisions_path(), data)


def load_stage_results() -> dict[str, Any]:
    data = read_json(stage_results_path(), {"stages": []})
    if not isinstance(data, dict):
        data = {"stages": []}
    if not isinstance(data.get("stages"), list):
        data["stages"] = []
    return data


def append_stage_result(stage_id: str, status: str, **extra: Any) -> dict[str, Any]:
    data = load_stage_results()
    entry = {"stage_id": stage_id, "status": status, **extra}
    data["stages"].append(entry)
    write_json(stage_results_path(), data)
    return entry


def parse_stage_response(response: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(response, dict):
        response = {}
    decision = str(response.get("decision") or response.get("action") or "run").strip().lower()
    if decision == "approve":
        decision = "run"
    if decision not in VALID_DECISIONS:
        raise ValueError(f"unsupported stage decision: {decision}")
    reason = response.get("reason") if isinstance(response.get("reason"), str) else ""
    return {"decision": decision, "reason": reason}


def resolve_stage_decision(stage_id: str, target: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]:
    auto_enabled = bool(decisions.get("auto_enabled")) or target.get("mode") == "auto"
    if auto_enabled and stage_id in AUTO_ALLOWED_STAGES:
        return {"route": "run", "source": "auto", "requires_approval": False}
    return {"route": "ask", "source": "manual", "requires_approval": True}


def record_stage_decision(stage_id: str, response: dict[str, Any] | None, *, source: str = "manual") -> dict[str, Any]:
    parsed = parse_stage_response(response)
    decisions = load_decisions()
    if parsed["decision"] == "auto":
        decisions["auto_enabled"] = True
        route = "run"
    else:
        route = parsed["decision"]
    entry = {
        "stage_id": stage_id,
        "decision": parsed["decision"],
        "route": route,
        "source": source,
        "reason": parsed["reason"],
    }
    decisions["stages"].append(entry)
    save_decisions(decisions)
    return entry


def enable_auto_for_stage(stage_id: str) -> dict[str, Any]:
    response = {"decision": "auto", "reason": "用户选择 auto"}
    write_json(stage_response_path(stage_id), response)
    return record_stage_decision(stage_id, response, source="auto")


def latest_stage_decision(stage_id: str) -> dict[str, Any] | None:
    decisions = load_decisions()
    for entry in reversed(decisions.get("stages", [])):
        if isinstance(entry, dict) and entry.get("stage_id") == stage_id:
            return entry
    return None


def finalize_stage_decision(stage_id: str) -> dict[str, Any]:
    existing = latest_stage_decision(stage_id)
    if existing and existing.get("source") == "auto":
        return existing
    return record_stage_decision(stage_id, read_stage_response(stage_id))


def prepare_stage_decision(stage_id: str, context: dict[str, Any]) -> dict[str, Any]:
    target = load_target()
    decisions = load_decisions()
    decision = resolve_stage_decision(stage_id, target, decisions)
    context = {**context, "stage_id": stage_id, "target": target, "decision": decision}
    if decision["route"] == "run":
        record_stage_decision(stage_id, {"decision": "run", "reason": "auto"}, source="auto")
    return context


def stage_response_path(stage_id: str) -> Path:
    return lgwf_dir() / "post_fix_decisions" / f"{stage_id}.json"


def read_stage_response(stage_id: str) -> dict[str, Any]:
    response = read_json(stage_response_path(stage_id), {"decision": "run"})
    return response if isinstance(response, dict) else {"decision": "run"}


def workflow_name_from_target(target: dict[str, Any]) -> str:
    workflow_lgwf = Path(str(target["target_workflow_lgwf"]))
    parent_name = workflow_lgwf.parent.name
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in parent_name).strip("_")
    return normalized or "workflow"


def resolve_workspace_path(path_value: str | Path) -> Path:
    path = Path(str(path_value)).expanduser()
    if path.is_absolute():
        return path
    candidates = [workspace_root(), *workspace_root().parents]
    for base in candidates:
        candidate = (base / path).resolve()
        if candidate.exists():
            return candidate
    for base in candidates:
        candidate = (base / path).resolve()
        if candidate.parent.exists():
            return candidate
    return (workspace_root() / path).resolve()


def target_package_root(target: dict[str, Any]) -> Path:
    root = target.get("target_package_root") or Path(str(target["target_workflow_lgwf"])).parent
    return resolve_workspace_path(str(root))


def generated_test_files(target: dict[str, Any]) -> dict[str, str]:
    root = target_package_root(target)
    prefix = workflow_name_from_target(target)
    tests = root / "tests"
    return {
        "script_flow_e2e": str(tests / f"test_{prefix}_script_flow_e2e.py"),
        "runtime_fake_e2e": str(tests / f"test_{prefix}_runtime_fake_e2e.py"),
        "real_positive_e2e": str(tests / f"lgwf_{prefix}_real_positive_e2e.py"),
        "wf_fix_positive_e2e": str(tests / f"lgwf_{prefix}_real_positive_e2e_for_wf_fix.py"),
    }


def run_python_file(stage_id: str, path: str, timeout: int = 900) -> dict[str, Any]:
    test_path = Path(path)
    if not test_path.exists():
        result = {"stage_id": stage_id, "status": "skipped", "reason": f"测试入口不存在: {path}", "path": path}
        append_stage_result(stage_id, "skipped", reason=result["reason"], path=path)
        return result
    completed = subprocess.run(
        [sys.executable, str(test_path)],
        cwd=str(test_path.parent),
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    status = "completed" if completed.returncode == 0 else "failed"
    result = {
        "stage_id": stage_id,
        "status": status,
        "path": path,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    append_stage_result(stage_id, status, path=path, returncode=completed.returncode)
    return result


def finish_decision_only_stage(stage_id: str, result_key: str, route_node: str) -> None:
    decision = finalize_stage_decision(stage_id)
    result = append_stage_result(stage_id, decision["route"], decision=decision)
    output_state(
        {result_key: result},
        next_key="stop" if decision["route"] == "stop" else "continue",
        route_node=route_node,
    )


def finish_or_record_stage_decision(stage_id: str, result_key: str, route_node: str) -> None:
    decision = latest_stage_decision(stage_id)
    if decision is None:
        decision = finalize_stage_decision(stage_id)
        append_stage_result(stage_id, decision["route"], decision=decision)
    route = "stop" if decision.get("route") == "stop" else "continue"
    output_state({result_key: route}, next_key=route, route_node=route_node)
