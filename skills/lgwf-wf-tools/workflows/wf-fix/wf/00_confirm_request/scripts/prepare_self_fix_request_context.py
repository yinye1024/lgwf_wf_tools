from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shared"))

from self_fix_common import output_state


def main() -> None:
    output_state(
        {
            "self_fix_request_context": {
                "instruction": "Confirm the target workflow.lgwf and fix retry limit before any repair work starts.",
                "required_fields": {
                    "target_workflow_lgwf": "Path to the target workflow.lgwf file.",
                },
                "optional_fields": {
                    "max_attempts": "Maximum repair attempts. Defaults to 5.",
                    "ask_main_agent_for_target_approvals": "Whether lgwf-wf-tools should forward target workflow APPROVAL requests to the main agent for confirmation. Defaults to false.",
                },
                "example": {
                    "target_workflow_lgwf": "D:/path/to/workflow.lgwf",
                    "max_attempts": 5,
                    "ask_main_agent_for_target_approvals": False,
                },
            }
        }
    )


if __name__ == "__main__":
    main()
