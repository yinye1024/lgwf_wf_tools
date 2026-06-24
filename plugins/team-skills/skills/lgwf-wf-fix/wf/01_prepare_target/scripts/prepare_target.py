from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import append_history, lgwf_dir, output_state, read_json, write_json


def normalize_request(raw: dict) -> dict:
    target = raw.get("target_workflow_lgwf")
    if not isinstance(target, str) or not target.strip():
        raise ValueError("input.target_workflow_lgwf is required")
    max_attempts = raw.get("max_attempts", 5)
    try:
        max_attempts_int = int(max_attempts)
    except (TypeError, ValueError) as exc:
        raise ValueError("input.max_attempts must be an integer") from exc
    if max_attempts_int < 1:
        raise ValueError("input.max_attempts must be >= 1")
    ask_main_agent_for_target_approvals = raw.get("ask_main_agent_for_target_approvals", False)
    if not isinstance(ask_main_agent_for_target_approvals, bool):
        raise ValueError("input.ask_main_agent_for_target_approvals must be a boolean")
    return {
        "target_workflow_lgwf": target,
        "max_attempts": max_attempts_int,
        "ask_main_agent_for_target_approvals": ask_main_agent_for_target_approvals,
    }


def build_target(request: dict, cwd: Path) -> dict:
    workflow_path = Path(request["target_workflow_lgwf"]).expanduser()
    if not workflow_path.is_absolute():
        workflow_path = (cwd / workflow_path).resolve()
    else:
        workflow_path = workflow_path.resolve()
    if not workflow_path.exists() or not workflow_path.is_file():
        raise FileNotFoundError(f"target workflow.lgwf not found: {workflow_path}")
    if workflow_path.name != "workflow.lgwf":
        raise ValueError("target_workflow_lgwf must point to a workflow.lgwf file")
    package_root = workflow_path.parent
    return {
        "target_workflow_lgwf": str(workflow_path),
        "target_package_root": str(package_root),
        "target_dirs": [str(package_root)],
        "max_attempts": request["max_attempts"],
        "ask_main_agent_for_target_approvals": request["ask_main_agent_for_target_approvals"],
        "current_attempt": 0,
        "last_status": "prepared",
    }


def main() -> None:
    root = Path.cwd()
    request_path = lgwf_dir(root) / "self_fix_request_input.json"
    request = normalize_request(read_json(request_path, {}))
    target = build_target(request, root)
    write_json(lgwf_dir(root) / "self_fix_request.json", request)
    write_json(lgwf_dir(root) / "self_fix_target.json", target)
    append_history({"event": "prepared", "target_workflow_lgwf": target["target_workflow_lgwf"]})
    output_state(
        {
            "request": request,
            "target": target,
            "target_dirs": target["target_dirs"],
            "input_collection_context": {
                "target_workflow_lgwf": target["target_workflow_lgwf"],
                "contract_path": ".lgwf/target_input_contract.json",
                "instruction": "Provide a JSON object to persist as .lgwf/target_workflow_input.json.",
            },
        }
    )


if __name__ == "__main__":
    main()
