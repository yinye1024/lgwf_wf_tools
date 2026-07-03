from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import append_stage_result, finalize_stage_decision, load_target, output_state, workflow_name_from_target


def build_e2e_input(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_lgwf": target["target_workflow_lgwf"],
        "workflow_root": target["target_package_root"],
        "test_output_dir": "tests",
        "test_name_prefix": workflow_name_from_target(target),
        "test_types": ["script_flow", "runtime_fake"],
    }


def main() -> None:
    decision = finalize_stage_decision("e2e_generate")
    target = load_target()
    payload = build_e2e_input(target)
    append_stage_result("e2e_generate", "ready", decision=decision)
    output_state(
        {"e2e_input": payload, "e2e_generate_stage_decision": decision},
    )


if __name__ == "__main__":
    main()
