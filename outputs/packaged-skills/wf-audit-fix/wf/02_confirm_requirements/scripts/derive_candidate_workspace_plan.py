from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import ensure_safe_candidate_dir, lgwf_dir, output_state, read_json, save_runtime_context


def main() -> None:
    context = read_json(lgwf_dir() / "runtime_context.json", {})
    base_dir = lgwf_dir() / "candidates" / "current"
    ensure_safe_candidate_dir(base_dir)
    workflow_name = Path(str(context["normalized_target_workflow_lgwf"])).parent.parent.name
    plan = {
        "candidate_root": str(base_dir),
        "candidate_package_root": str(base_dir / workflow_name),
        "candidate_workflow_lgwf": str(base_dir / workflow_name / "wf" / "workflow.lgwf"),
    }
    context["candidate_workspace_plan"] = plan
    context["runtime_context"] = {
        "target_workflow_lgwf": context["normalized_target_workflow_lgwf"],
        "target_package_root": context["resolved_target_package_root"],
        "candidate_workspace_plan": plan,
        "attempt_policy": context.get("attempt_policy", {"max_attempts": 5, "hard_cap": 20}),
    }
    save_runtime_context(context)
    output_state({"candidate_workspace_plan": plan, "runtime_context": context["runtime_context"]})


if __name__ == "__main__":
    main()
