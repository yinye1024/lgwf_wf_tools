from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared" / "scripts"))

from post_fix_common import append_stage_result, finalize_stage_decision, generated_test_files, load_target, output_state, run_python_file


def main() -> None:
    decision = finalize_stage_decision("wf_fix_positive_e2e")
    if decision["route"] == "run":
        result = run_python_file(
            "wf_fix_positive_e2e",
            generated_test_files(load_target())["wf_fix_positive_e2e"],
            timeout=1800,
        )
    else:
        result = append_stage_result("wf_fix_positive_e2e", decision["route"], decision=decision)
    output_state(
        {"wf_fix_positive_e2e_result": result},
        next_key="stop" if decision["route"] == "stop" else "continue",
        route_node="route_wf_fix_positive",
    )


if __name__ == "__main__":
    main()
