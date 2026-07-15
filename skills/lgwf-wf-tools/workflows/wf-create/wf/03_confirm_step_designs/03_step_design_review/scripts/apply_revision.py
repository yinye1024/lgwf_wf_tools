"""将步骤设计的 revise 决策写回 canonical proposal。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "shared" / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))

from confirmation_io import write_revised_proposal
from prepare_step_design_revision_confirmation import build_context


APPROVAL_FILE = "step_design_confirmation_record.json"
PROPOSAL_FILE = "step_designs_proposal.json"


def main() -> None:
    lgwf_dir = Path.cwd() / ".lgwf"
    result = write_revised_proposal(
        lgwf_dir=lgwf_dir,
        approval_file=APPROVAL_FILE,
        approval_key="step_design_confirmation_record",
        proposal_file=PROPOSAL_FILE,
        normalized_path_fields=("target_package_root", "approved_step_designs_path", "step_designs_path"),
    )
    context = build_context(Path.cwd())
    print(
        json.dumps(
            {
                "lgwf_wf_create.step_design_revision_result": result,
                "lgwf_wf_create.step_designs_proposal": result["proposal"],
                "lgwf_wf_create.step_design_revision_context": context,
                "lgwf_wf_create.step_design_confirmation_context": context,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
