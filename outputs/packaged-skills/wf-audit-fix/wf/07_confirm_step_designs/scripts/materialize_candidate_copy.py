from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from audit_fix_common import copy_tree, lgwf_dir, load_runtime_context, output_state, write_json


def main() -> None:
    context = load_runtime_context()
    plan = context["candidate_workspace_plan"]
    source = Path(str(context["resolved_target_package_root"]))
    destination = Path(str(plan["candidate_package_root"]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy_tree(source, destination)
    snapshot = {
        "candidate_package_root": str(destination),
        "candidate_workflow_lgwf": str(Path(str(plan["candidate_workflow_lgwf"]))),
    }
    write_json(lgwf_dir() / "candidate_pass_snapshot.json", {})
    output_state(
        {
            "candidate_snapshot": snapshot,
            "candidate_target_dirs": [str(destination)],
        }
    )


if __name__ == "__main__":
    main()
