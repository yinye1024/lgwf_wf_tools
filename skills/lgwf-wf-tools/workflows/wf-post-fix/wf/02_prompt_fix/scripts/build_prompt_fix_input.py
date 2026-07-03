from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import append_stage_result, finalize_stage_decision, load_target, output_state


def build_prompt_fix_input(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt_fix_target": {
            "target_workflow_lgwf": target["target_workflow_lgwf"],
            "target_package_root": target["target_package_root"],
            "target_dirs": target["target_dirs"],
        }
    }


def main() -> None:
    decision = finalize_stage_decision("prompt_fix")
    target = load_target()
    payload = build_prompt_fix_input(target)
    append_stage_result("prompt_fix", "ready", decision=decision)
    output_state(
        {"prompt_fix_input": payload, "prompt_fix_stage_decision": decision},
    )


if __name__ == "__main__":
    main()
