from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir
from target_repair_loop import load_current_artifact, write_current_artifact


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _failure_signals(observation: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for key in ("status", "phase", "failure_class", "error", "last_error", "blocked_reason"):
        if observation.get(key):
            signals.append({"source": "observation", "field": key, "value": observation[key]})
    for issue in _as_list(observation.get("issues")):
        signals.append({"source": "observation.issues", "value": issue})
    status = _as_dict(observation.get("status_detail") or observation.get("status"))
    if status.get("last_error"):
        signals.append({"source": "observation.status", "field": "last_error", "value": status["last_error"]})
    return signals


def _contract_signals(observation: dict[str, Any]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    contract_audit = _as_dict(observation.get("contract_audit"))
    for issue in _as_list(contract_audit.get("issues")):
        signals.append({"source": "contract_audit.issues", "value": issue})
    for stale in _as_list(contract_audit.get("stale_expectations")):
        signals.append({"source": "contract_audit.stale_expectations", "value": stale})
    if observation.get("failure_class") in {"contract_drift", "output_contract"}:
        signals.append(
            {
                "source": "observation.failure_class",
                "value": observation.get("failure_class"),
                "meaning": "target output contract may be inconsistent with actual workflow topology or artifacts",
            }
        )
    return signals


def _run_health_signals(observation: dict[str, Any]) -> list[dict[str, Any]]:
    health = _as_dict(observation.get("run_health"))
    signals: list[dict[str, Any]] = []
    for key, value in sorted(health.items()):
        if value:
            signals.append({"source": "run_health", "field": key, "value": value})
    return signals


def _workspace_state(workspace: dict[str, Any]) -> dict[str, Any]:
    candidate = Path(str(workspace.get("candidate_package_root") or ""))
    baseline = Path(str(workspace.get("baseline_package_root") or ""))
    return {
        "candidate_package_root": workspace.get("candidate_package_root"),
        "candidate_exists": candidate.exists(),
        "baseline_package_root": workspace.get("baseline_package_root"),
        "baseline_exists": baseline.exists(),
        "candidate_workflow_lgwf": workspace.get("candidate_workflow_lgwf"),
        "target_dirs": workspace.get("target_dirs") or [],
        "target_files": workspace.get("target_files") or [],
    }


def _previous_iteration_summary(root: Path) -> dict[str, Any]:
    diagnosis = _as_dict(load_current_artifact(root, "diagnosis", {}))
    plan = _as_dict(load_current_artifact(root, "plan", {}))
    apply_result = _as_dict(load_current_artifact(root, "apply", {}))
    verification = _as_dict(load_current_artifact(root, "verification", {}))
    change_audit = _as_dict(load_current_artifact(root, "change_audit", {}))
    decision = _as_dict(load_current_artifact(root, "decision", {}))
    return {
        "diagnosis": {
            "failure_class": diagnosis.get("failure_class"),
            "root_cause": diagnosis.get("root_cause"),
            "confidence": diagnosis.get("confidence"),
            "auto_fixable": diagnosis.get("auto_fixable"),
            "blocked_reason": diagnosis.get("blocked_reason"),
        },
        "plan": {
            "status": plan.get("status"),
            "files_to_modify": plan.get("files_to_modify") or [],
            "blocked_reason": plan.get("blocked_reason"),
        },
        "apply": {
            "status": apply_result.get("status"),
            "changed_files": apply_result.get("changed_files") or [],
            "blocked_reason": apply_result.get("blocked_reason"),
        },
        "verification": {
            "passed": verification.get("passed"),
            "failed_checks": verification.get("failed_checks") or [],
            "retry_hints": verification.get("retry_hints") or [],
            "unexpected_changes": verification.get("unexpected_changes") or [],
            "validation_failures": verification.get("validation_failures") or [],
            "semantic_review_needed": verification.get("semantic_review_needed") is True,
            "semantic_risks": verification.get("semantic_risks") or [],
        },
        "change_audit": {
            "passed": change_audit.get("passed"),
            "unexpected_changes": change_audit.get("unexpected_changes") or [],
            "missing_planned_changes": change_audit.get("missing_planned_changes") or [],
        },
        "decision": {
            "category": decision.get("category"),
            "stop_reason": decision.get("stop_reason"),
            "reason": decision.get("reason"),
        },
    }


def build_observation(root: Path) -> dict:
    observation = load_current_artifact(root, "observation", {})
    run = load_current_artifact(root, "run", {})
    workspace = load_current_artifact(root, "workspace", {})
    observation = _as_dict(observation)
    run = _as_dict(run)
    workspace = _as_dict(workspace)
    enhanced_observation = dict(observation)
    enhanced_observation["failure_signals"] = _failure_signals(observation)
    enhanced_observation["contract_signals"] = _contract_signals(observation)
    enhanced_observation["run_health_signals"] = _run_health_signals(observation)
    enhanced_observation["candidate_workspace_state"] = _workspace_state(workspace)
    enhanced_observation["previous_iteration_summary"] = _previous_iteration_summary(root)
    return {
        "status": enhanced_observation.get("status", "unknown"),
        "phase": enhanced_observation.get("phase"),
        "failure_class": enhanced_observation.get("failure_class"),
        "failure_signals": enhanced_observation["failure_signals"],
        "contract_signals": enhanced_observation["contract_signals"],
        "run_health_signals": enhanced_observation["run_health_signals"],
        "candidate_workspace_state": enhanced_observation["candidate_workspace_state"],
        "previous_iteration_summary": enhanced_observation["previous_iteration_summary"],
        "observation": enhanced_observation,
        "run": run,
        "workspace": workspace,
    }


def main() -> None:
    root = lgwf_dir()
    result = build_observation(root)
    write_current_artifact(root, "observation", result["observation"])
    append_history({"event": "repair_agent_loop_observed", "status": result["status"], "phase": result.get("phase")})
    print(json.dumps({"lgwf_wf_fix.target_repair_observe_result": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
